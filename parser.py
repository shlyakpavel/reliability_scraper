import re
import itertools
from statistics import mean
from collections import Counter
from yargy.interpretation import fact
from yargy import rule, Parser, or_, not_, and_
from yargy.predicates import eq, type
from yargy.pipelines import morph_pipeline
from doitrust import score

def yargy_parser(path):
    RULE = fact(
        'RULE',
        ['name', 'tresh', 'num']
    )
    INT = type('INT')
    PUNCT = type('PUNCT')

    DOT = or_(eq('.'), eq(','))

    NAME_mtbf = morph_pipeline(
        [
            'MTTF',
            'MTBF',
            'mean time between',
            'mean time between failures',
            'mean time between failure',
        ]
    ).interpretation(
        RULE.name
    )

    NAME_mttr = morph_pipeline(
        [
            'MTTR',
            'mean time to',
            'Mean Time To Repair',
            'repair time',
        ]
    ).interpretation(
        RULE.name
    )

    NUM_MTBF = or_(rule(INT, DOT, INT), rule(INT),
                   rule(INT, DOT, INT, DOT, INT),
                   rule(INT, INT), rule(INT, INT, INT))

    UNIT_mtbf = morph_pipeline(
        [
            'year',
            'years',
            'hour',
            'hours',
            'год',
            'час',
            'h',
            'ч',
            'тыс. часов'
        ]
    )

    UNIT_mttr = morph_pipeline(
        [
            'hour',
            'hours',
            'час',
            'h',
            'ч',
            'мин',
            'minutes',
            'minute',
            'минут'
        ]
    )

    X_mtbf = rule(NUM_MTBF, UNIT_mtbf.optional()
                 ).interpretation(
                     RULE.num
                 )

    X_mttr = rule(INT, UNIT_mttr.optional()
                 ).interpretation(
                     RULE.num
                 )

    TRESH = rule(and_(not_(eq(NUM_MTBF)), or_(not_(eq(NAME_mttr)),
                                              not_(eq(NAME_mtbf))),
                      not_(eq(UNIT_mtbf)), not_(eq(DOT)),
                      not_(eq(INT)), not_(eq(X_mttr)), not_(eq(X_mtbf)))
                ).interpretation(
                    RULE.tresh
                )

    rule_1 = (rule(NAME_mtbf, (TRESH.optional()).repeatable(), X_mtbf).repeatable()
             ).interpretation(
                 RULE
             )

    rule_2 = (rule(NAME_mttr, (TRESH.optional()).repeatable(), X_mttr).repeatable()
             ).interpretation(
                 RULE
             )

    f = open(path, 'r')
    text = f.read()
    text = text.replace('|',' ')
    #Remove line separators
    text = re.sub("^\s+|\n|\r|\s+$", '', text)
    line = text
    #Temporary workaround. Remove it as the performance grows
    n = 10000
    text = [line[i-5 if i-5 > 0 else 0:i+n+5 if i+n+5 < len(line)
                 else len(line) -1] for i in range(0, len(line), n)]
    MEASURE = rule(or_(X_mttr, X_mtbf, NAME_mttr, NAME_mtbf))
    new_line = []
    #Parser #1 text preprocessing
    parser = Parser(MEASURE)
    for line in text:
        matches = list(parser.findall(line))
        spans = [_.span for _ in matches]
        new_span = [0, 0]
        if spans != [] and len(spans) >= 2:
            for i in range(0, len(spans)-1, 1):
                mini = 1000000
                maxi = 0
                if spans[i][0] < mini:
                    new_span[0] = spans[i][0]
                    mini = spans[i][0]
                if spans[i+1][1] > maxi:
                    new_span[1] = spans[i+1][1]
                    maxi = spans[i+1][1]
                for i in range(new_span[0], new_span[1]):
                    new_line.append(line[i])
                new_line.append(' \n ')
    new_line = ''.join(new_line)
    new_line = new_line.split('\n')
    LIST = []
    MEASURE = or_(rule_1, rule_2).interpretation(
        RULE
    )
    #Parser #2 Parsing reliability metrics.
    parser = Parser(MEASURE)
    for line in new_line:
        try:
            matches = list(parser.findall(line))
            spans = [_.span for _ in matches]
            if spans != []:
                if matches:
                    for match in matches:
                        LIST.append(match.fact)
        except:
            print('Yargy failure: you normally don`t need to report that to us.')
    print(LIST)
    return LIST

def calculate_param(dict_max):
    try:
        dict_max['Failure rate'] = 1/dict_max['MTBF']
    except:
        dict_max['Failure rate'] = 0
    dict_max['failure rate in storage mode'] = dict_max['Failure rate'] * 0.01
    try:
        dict_max['Storage time'] = round(1/(dict_max['failure rate in storage mode']*8760), 3)
    except:
        dict_max['Storage time'] = 0
    dict_max['Minimal resource'] = round(0.01*dict_max['MTBF'], 3)
    dict_max['Gamma percentage resource'] = round(0.051239*dict_max['MTBF'], 3)
    dict_max['Average resource'] = round(0.6931*dict_max['MTBF'], 3)
    dict_max['Average lifetime'] = round(dict_max['Average resource']/8760, 3)
    try:
        dict_max['recovery intensity'] = 1/dict_max['MTTR']
    except:
        dict_max['recovery intensity'] = 0
    try:
        if (dict_max['MTBF'] != 0 and dict_max['MTTR'] != 0):
            dict_max['System Reliability'] = dict_max['MTBF']/(dict_max['MTBF']+dict_max['MTTR'])
        else:
            dict_max['System Reliability'] = 0
    except:
        dict_max['System Reliability'] = 0
    return dict_max

def strip_num(string):
    """There are several options for input numbers
    '1,123,234 year/hours', '1123234.5 year/hours', '1123234.5'
    '1 123 234 year/hours', '1 123 234'
    """
    #At first we replace ',' to '' and split string for grabbing the number
    src_list = string.replace(',', '').split(' ')
    #TODO: avoid try-except
    try:
        #Here we grab the number when possible.
        #This is possible when the number is without a unit
        number = int(float(''.join(src_list)))
    except:
        try:
            #Delete the unit so only num remains
            del src_list[-1]
            number = int(float(''.join(src_list)))
        except:
            print(src_list)
            print('Error convert')
            number = 0
    return number

def to_hours(string):
    """ Converts stuff like '13 years' or '13 тыс. часов' into hours """
    result = 0
    if ('years' in string
            or 'year' in string
            or 'год' in string):
        try:
            num = float((string).split(' ')[0])
            num = num * 8760
            result = int(round(num))
        except:
            print('Error with float')
    #TODO: apply all possible cases
    elif 'тыс. часов' in string:
        try:
            num = float((string).split(' ')[0])
            num = num * 1000
            result = int(round(num))
        except:
            print('Error with float')
    elif ('minute' in string
             or 'мин' in string):
        try:
            num = float((string).split(' ')[0])
            result = num/60
        except:
            print('Error with float')
    else:
        result = strip_num(string)
    return result

def finding_num(parsed, query):
    #MTTF is listed as a synonym to MBTF as their difference is
    #more about recovery than about the time. They are almost
    #identical then it comes to calculating probabilities
    names_mtbf = ['mtbf', 'mttf',
                  'mean time between',
                  'mean time between failures',
                  'mean time between failure',]
    names_mttr = ['mttr',
                  'mean time to',
                  'mean time to repair',
                  'mean time to repairs',
                  'repair time']
    dict_num = {'MTTR':[], 'MTBF':[]}
    dict_links = {'MTTR':{}, 'MTBF':{}}
    dict_max = {'MTTR':0, 'MTBF':0, 'Links':[]}
    score_max = 0
    for link in parsed:
        for item in parsed[link]:
            #Unify titles
            if item.name.lower() in names_mtbf:
                item.name = 'MTBF'
            elif item.name.lower() in names_mttr:
                item.name = 'MTTR'
            item.num = to_hours(item.num)
            # TODO: fix multiline recognition.
            # Temporary workaround
            if item.name == 'MTTR' and item.num > 20:
                item.num = item.num/60
            dict_num[item.name].append(item.num)
            if item.num in dict_links[item.name]:
                if not link in dict_links[item.name][item.num]:
                    dict_links[item.name][item.num].append(link)
            else:
                dict_links[item.name][item.num] = [link]
    #Set maximum delta (%)
    max_delta = 5
    for param_name in dict_num:
        values = dict_num[param_name]
        counted_values = dict(Counter(values))
        #Join close and equal values
        deleted = []
        for first_value, second_value in itertools.permutations(counted_values.keys(), 2):
            if first_value in deleted or second_value in deleted:
                continue
            delta = 100 * abs(first_value - second_value) / mean([first_value, second_value])
            #If the difference is less than delta and values are not equal
            #Keep in mind we are iterating the same dict twice
            if delta < max_delta:
                to_keep = 0
                to_replace = 0
                if counted_values[first_value] >= counted_values[second_value]:
                    to_keep = first_value
                    to_replace = second_value
                else:
                    to_keep = second_value
                    to_replace = first_value
                deleted.append(to_replace)
                #Recount
                counted_values[to_keep] += counted_values[to_replace]
                del counted_values[to_replace]
                #Merge links
                if dict_links[param_name][to_keep] != dict_links[param_name][to_replace]:
                    dict_links[param_name][to_keep] += dict_links[param_name][to_replace]
                del dict_links[param_name][to_replace]
        #Default values
        amount_res = 0
        value_res = 0
        links_res = []
        #Drop insane values and find the most popular one
        for num in counted_values:
            if ((param_name == 'MTTR' and 0 < num < 100) or
                    (param_name == 'MTBF' and num > 50000)):
                if counted_values[num] > amount_res:
                    amount_res = counted_values[num]
                    value_res = num
                    links_res = dict_links[param_name][value_res]
        dict_max[param_name] = value_res
        for link in links_res:
            if not link in dict_max['Links']:
                dict_max['Links'].append(link)
        #Amount_res can be greater than amount of links
        #as the same value can be providen twice on
        #the same resource. Thus, we use amount_res
        cur_score = score(links_res, amount_res, query)
        #Divide cur_score by params
        score_max += cur_score / len(dict_num)
    dict_max = calculate_param(dict_max)
    dict_max['score'] = int(score_max)
    print(dict_max)
    return dict_max

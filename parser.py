import re
from yargy.interpretation import fact
from yargy import rule, Parser, or_, not_, and_
from yargy.predicates import eq, type
from yargy.pipelines import morph_pipeline

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
            'ч'
        ]
    )

    UNIT_mttr = morph_pipeline(
        [
            'hour',
            'hours',
            'час',
            'h',
            'ч'
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
    #Remove line separators
    text = re.sub("^\s+|\n|\r|\s+$", '', text)
    line = text
    MEASURE = rule(or_(X_mttr, X_mtbf, NAME_mttr, NAME_mtbf))
    new_line = []
    #Parser #1 text preprocessing
    parser = Parser(MEASURE)
    matches = list(parser.findall(line))
    spans = [_.span for _ in matches]
    new_span = [0, 0]
    if len(spans) >= 2:
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
        matches = list(parser.findall(line))
        spans = [_.span for _ in matches]
        if spans != []:
            if matches:
                for match in matches:
                    LIST.append(match.fact)
    print(LIST)
    return LIST

def count_param(dict_max):
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

def finding_num(b):
    names_mtbf = ['mtbf',
                  'mean time between',
                  'mean time between failures',
                  'mean time between failure',]
    names_mttr = ['mttr',
                  'mean time to',
                  'mean time to repair',
                  'mean time to repairs',
                  'repair time']
    dict_num = {'MTTR':{}, 'MTBF':{}}
    dict_links = {'MTTR':{}, 'MTBF':{}}
    dict_max = {'MTTR':0, 'MTBF':0, 'Links':[]}
    dict_max_num = {'MTTR':0, 'MTBF':0}
    for link in b:
        for i in range(len(b[link])):
            if b[link][i].name.lower() in names_mtbf:
                b[link][i].name = 'MTBF'
            elif b[link][i].name.lower() in names_mttr:
                b[link][i].name = 'MTTR'
            if ('years' or 'year' or 'год') in b[link][i].num:
                try:
                    num = float((b[link][i].num).split(' ')[0])
                    num = num * 8760
                    b[link][i].num = int(round(num))
                except:
                    print('Error with float')
            else:
                #There are several options for input numbers
                #'1,123,234 year/hours', '1123234.5 year/hours', '1123234.5'
                #'1 123 234 year/hours', '1 123 234'
                #At first we replace ',' to '' and split string for grabbing the number
                b[link][i].num = b[link][i].num.replace(',', '').split(' ')
                try:
                    #Here we grabbing the number if it is possible.
                    #This could be possible if number was without units
                    b[link][i].num = int(float(''.join(b[link][i].num)))
                except:
                    #Else we delete units and remain only num
                    del b[link][i].num[len(b[link][i].num)-1]
                    b[link][i].num = int(float(''.join(b[link][i].num)))
            try:
                dict_num[b[link][i].name][b[link][i].num] += 1
            except:
                dict_num[b[link][i].name][b[link][i].num] = 1
            dict_links[b[link][i].name][b[link][i].num] = link
    #Matching value is the most repeatable one.
    for name in ['MTBF', 'MTTR']:
        for num in dict_num[name]:
            if dict_num[name][num] > dict_max_num[name]:
                checker = False
                if (name == 'MTTR' and 0 < num < 100):
                    checker = True
                if (name == 'MTBF' and num > 100000):
                    checker = True
                if checker:
                    dict_max_num[name] = dict_num[name][num]
                    dict_max[name] = num
                    if not dict_links[name][num] in dict_max['Links']:
                        dict_max['Links'].append(dict_links[name][num])
    dict_max = count_param(dict_max)
    print(dict_max)
    return dict_max

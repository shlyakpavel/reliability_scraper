import ssl
import socket
from urllib.parse import urlsplit


def check_ssl_ev(hostname):
    """Check if SSL EV is available"""
    try:
        result = []
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(socket.socket(), server_hostname=hostname)
        s.connect((hostname, 443))
        cert = s.getpeercert()
        s.close()
        subject = dict(x[0] for x in cert['subject'])
        result.append("serialNumber" in subject)
        result.append(subject["organizationName"])
    except (ssl.SSLError, ConnectionError, KeyError):
        result = [False, '']
    return result


def score(links, amount, query):
    """Are the sources trustworthy?"""
    query = query.lower().split(' ')
    result = 1
    # One link per site is a good idea, we didn't catch
    # a model name or a catalog
    if links == amount:
        result += 2
    # Amount of matches gives maximum three points
    if amount < 3:
        result += amount
    else:
        result = 3
    ssl_score = 0
    domain_matches = False
    for link in links:
        url = urlsplit(link)
        if url.scheme == 'https':
            ssl_ev = check_ssl_ev(url.netloc)
            if ssl_ev[0]:
                ssl_score += 2
            for part_query in query:
                domain_matches = domain_matches or ( part_query in ssl_ev[1].lower() )
    if domain_matches:
        ssl_score += 2
    # SSL in summary should be no more than 4 points
    if ssl_score < 4:
        result += ssl_score
    else:
        result += 4
    return result

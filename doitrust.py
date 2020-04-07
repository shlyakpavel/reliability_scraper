import ssl
import socket
from urllib.parse import urlsplit


def check_ssl_ev(hostname):
    """Check if SSL EV is available"""
    try:
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(socket.socket(), server_hostname=hostname)
        s.connect((hostname, 443))
        cert = s.getpeercert()
        s.close()
        subject = dict(x[0] for x in cert['subject'])
        result = ("serialNumber" in subject)
    except ssl.SSLError:
        result = False
    return result


def score(links, amount):
    """Are the sources trustworthy?"""
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
    for link in links:
        url = urlsplit(link)
        if url.scheme == 'https':
            if check_ssl_ev(url.netloc):
                ssl_score += 2
    # SSL is no more than 4 points
    if ssl_score < 4:
        result += ssl_score
    else:
        result += 4
    return result

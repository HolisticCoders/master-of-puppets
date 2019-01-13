"""Change string objects case."""
import re
from operator import methodcaller


#: Pattern matching characters that will be replaced by the case
#: preferred separator character.
#:
#: :type: re.RegexObject
SEPARATORS = re.compile(r'[!"#$%&\'\(\)\*\+\,/:;<=>?@\^_`{|}~\-\s]')


#: Pattern matching characters that marks the end of a word.
#:
#: Unlike `SEPARATORS`, these characters will be preserved in the
#: output string and be converted to upper or lower case depending
#: on the case you use.
#:
#: :type: re.RegexObject
STOPCHARS = re.compile(r'[A-Z]')


def camel(string):
    """Return the ``camelCase`` version of the input string.

    :param string: String to return in camel case.
    :type string: str
    :rtype: str
    """
    tokens = re.split(SEPARATORS, string)
    return tokens[0][0].lower() + tokens[0][1:] + ''.join([s.title() for s in tokens[1:]])


def pascal(string):
    """Return the ``PascalCase`` version of the input string.

    :param string: String to return in pascal case.
    :type string: str
    :rtype: str
    """
    tokens = re.split(SEPARATORS, string)
    return ''.join([s.title() for s in tokens])


def snake(string):
    """Return the ``snake_case`` version of the input string.

    :param string: String to return in snake case.
    :type string: str
    :rtype: str
    """
    return _convert_with_stops(string, '_', 'lower')


def kebab(string):
    """Return the ``kebab-case`` version of the input string.

    :param string: String to return in kebab case.
    :type string: str
    :rtype: str
    """
    return _convert_with_stops(string, '-', 'lower')


def header(string):
    """Return the ``Header-Case`` version of the input string.

    :param string: String to return in header case.
    :type string: str
    :rtype: str
    """
    tokens = re.split(SEPARATORS, string)
    return '-'.join([s.title() for s in tokens])


def constant(string):
    """Return the ``CONSTANT_CASE`` version of the input string.

    :param string: String to return in constant case.
    :type string: str
    :rtype: str
    """
    return _convert_with_stops(string, '_', 'upper')


def sentence(string):
    """Return the ``Sentence case`` version of the input string.

    :param string: String to return in sentence case.
    :type string: str
    :rtype: str
    """
    string = _convert_with_stops(string, ' ')
    if not string:
        return ''
    return string[0].upper() + string[1:]


def title(string):
    """Return the ``Title Case`` version of the input string.

    :param string: String to return in title case.
    :type string: str
    :rtype: str
    """
    return sentence(string).title()


def _convert_with_stops(string, separator, token_method=None):
    """Return ``string`` with ``separator`` inserted between `STOPCHARS`.

    You can also specify a ``token_method`` parameter to call
    ``str.token_method`` before the result is joined with ``separator``.

    For example::

        >>> _convert_with_stops('MyString', '-')
        'my-string'
        >>> _convert_with_stops('MyString', '-', 'upper')
        'MY-STRING'

    :param string: String to convert.
    :param separator: Character used to join generated string tokens.
    :param token_method: `str` method to call on each token before
                         joining them.
    :type string: str
    :type separator: str
    :type token_method: str
    :rtype: str
    """
    # Begin by converting normal separators to ``separator``.
    tokens = re.split(SEPARATORS, string)
    res = separator.join(tokens)

    # Collect indices where we have `STOPCHARS` characters.
    indices = []
    # Keep track of sequences of `STOPCHARS` and preserve them.
    _all_indices = []
    previous_was_stop = False
    for match in re.finditer(STOPCHARS, res):
        if not match:
            continue
        start = match.start()
        _all_indices.append(start)
        if start == 0:
            continue
        previous_was_stop = start - 1 in _all_indices
        if previous_was_stop:
            continue
        indices.append(start)

    # Insert underscores where we need them, and convert
    # everything to upper case.
    res = list(res)
    for index in reversed(indices):
        res.insert(index, separator)
    tokens = ''.join(res).split(separator)
    if token_method is None:
        return separator.join(tokens)
    return separator.join(map(methodcaller(token_method), tokens))

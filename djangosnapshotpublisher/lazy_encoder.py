"""
LazyEncoder
"""

from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder

class LazyEncoder(DjangoJSONEncoder):
    """ LazyEncoder """

    def default(self, o):
        """ default """
        if isinstance(o, Promise):
            return force_text(o)
        return super(LazyEncoder, self).default(o)

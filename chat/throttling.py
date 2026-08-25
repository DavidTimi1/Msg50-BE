from rest_framework.throttling import SimpleRateThrottle, AnonRateThrottle, UserRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    scope = 'auth'
    rate = '5/min'

class MediaUploadRateThrottle(UserRateThrottle):
    scope = 'media_upload'
    rate = '20/min'

class PublicKeyRateThrottle(UserRateThrottle):
    scope = 'public_key'
    rate = '100/min'

class FeedbackRateThrottle(SimpleRateThrottle):
    scope = 'feedback'
    rate = '10/hour'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.user.pk
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

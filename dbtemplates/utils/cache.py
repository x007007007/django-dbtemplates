from django.core import signals
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from dbtemplates.conf import settings


def get_cache_backend():
    """
    Compatibilty wrapper for getting Django's cache backend instance
    """
    from django.core.cache import _create_cache
    cache = _create_cache(settings.DBTEMPLATES_CACHE_BACKEND)
    # Some caches -- python-memcached in particular -- need to do a cleanup at
    # the end of a request cycle. If not implemented in a particular backend
    # cache.close is a no-op
    signals.request_finished.connect(cache.close)
    return cache

cache = get_cache_backend()


def get_cache_key(name, site=None):
    if site is None:
        current_site = Site.objects.get_current()
    else:
        current_site = site
    return 'dbtemplates::%s::%s' % (slugify(name), current_site.pk)


def get_cache_notfound_key(name, site=None):
    return get_cache_key(name, site=site) + '::notfound'


def remove_notfound_key(instance, site=None):
    # Remove notfound key as soon as we save the template.
    cache.delete(get_cache_notfound_key(instance.name, site=site))


def set_and_return(cache_key, content, display_name):
    # Save in cache backend explicitly if manually deleted or invalidated
    if cache:
        cache.set(cache_key, content)
    return (content, display_name)


def add_template_to_cache(instance, **kwargs):
    """
    Called via Django's signals to cache the templates, if the template
    in the database was added or changed.
    """
    from ..models import Template
    assert isinstance(instance, Template)
    remove_cached_template(instance)
    for site in instance.sites.all():
        remove_notfound_key(instance, site)
        cache.set(get_cache_key(instance.name, site), instance.content)


def remove_cached_template(instance, **kwargs):
    """
    Called via Django's signals to remove cached templates, if the template
    in the database was changed or deleted.
    """
    from ..models import Template
    assert isinstance(instance, Template)
    for site in instance.sites.all():
        cache.delete(get_cache_key(instance.name, site))

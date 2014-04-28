import json
import logging
from datetime import date, time, datetime
from collections import defaultdict
from itertools import chain
from itertools import product
from django.http import QueryDict

from subscriptions.feeds import ContentFeed
from subscriptions.feeds import ContentFeedLibrary
from phillyleg.models import LegFile
from phillyleg.models import LegMinutes
from haystack.query import SearchQuerySet
from urllib import urlencode

log = logging.getLogger(__name__)
library = ContentFeedLibrary()

class NewLegislationFeed (ContentFeed):
    def get_content(self):
        return LegFile.objects.all().order_by('-intro_date')

    def get_updates_since(self, datetime):
        return self.get_content().filter(intro_date__gt=datetime)

    def get_changes_to(self, legfile, since_datetime):
        if since_datetime.date() <= legfile.intro_date:
            return {'Title': legfile.title}, datetime.combine(legfile.intro_date, time())
        else:
            return {}, datetime.min

    def get_last_updated_time(self):
        legfiles = self.get_content()
        return legfiles[0].intro_date

    def get_params(self):
        return {}

    def get_label(self):
        return 'Newly introduced legislation'


class LegislationUpdatesFeed (ContentFeed):
    manager = LegFile.objects

    def __init__(self, **selectors):
        self.selectors = selectors

    def get_content(self):
        if self.selectors:
            return self.manager.filter(**self.selectors)
        else:
            return self.manager.all()

    def get_updates_since(self, datetime):
        return [content_item for content_item in self.get_content()
                if self.get_last_updated_time_for_file(content_item) > datetime.date()]

    def get_changes_to(self, legfile, since_datetime):
        changes = defaultdict(unicode)
        dates = set()
        for action in legfile.actions.all():
            if action.date_taken > since_datetime.date():
                if 'Actions' in changes:
                    changes['Actions'] += u'\n'
                changes['Actions'] += unicode(action)
                dates.add(action.date_taken)

        if changes:
            return changes, datetime.combine(max(dates), time())
        else:
            return {}, datetime.min

    def get_last_updated_time(self):
        dates = set()
        for legfile in self.get_content():
            dates.add(self.get_last_updated_time_for_file(legfile))

        return max(dates)

    def get_last_updated_time_for_file(self, legfile):
        legfile_date = max(legfile.intro_date,
                           legfile.final_date or date(1970, 1, 1))
        action_dates = [action.date_taken
                        for action in legfile.actions.all()]

        return max([legfile_date] + action_dates)

    def get_params(self):
        return self.selectors

    def get_label(self):
        return 'Updates to legislation'


from django.dispatch import receiver
from django.db.models.signals import post_save
from subscriptions.models import Subscriber

@receiver(post_save, sender=Subscriber)
def create_bookmarks_subscription_for_subscriber(sender, **kwargs):
    """
    Create a Subscriber object whenever a user is created.  This is useful so
    that we don't have to patch whatever different registration processes we
    end up using.
    """
    subscriber = kwargs.get('instance')
    created = kwargs.get('created')
    raw = kwargs.get('raw')

    logging.info('subscriber is %r' % subscriber)

    if created and not raw:
        feed = BookmarkedContentFeed(subscriber)
        try:
            if subscriber.subscription(feed) is None:
                subscriber.subscribe(feed)
                logging.info('created bookmarks subscription')
        except BookmarkedContentFeed.NotFound, e:
            logging.warning(e)


class BookmarkedContentFeed (LegislationUpdatesFeed):
    def __init__(self, user):
        if isinstance(user, (int, basestring)):
            try:
                self.user = Subscriber.objects.get(pk=user)
            except Subscriber.DoesNotExist, e:
                raise self.IsObsolete(e)
        else:
            self.user = user

    def get_content(self):
        # This results in N queries, but could be achieved in 1.
        # Should probably be optimized.
        return [bookmark.content for bookmark in self.user.bookmarks.all()]

    def get_params(self):
        return {'user': self.user.pk}

    def get_label(self):
        return 'Content that you have bookmarked ({0} items)'.format(self.user.bookmarks.count())


class SearchResultsFeed (ContentFeed):
    def __init__(self, search_filter):
        """
        As you'll see in main.SearchView.get_content_feed, we use the value of
        search_view.results.queryset.query.query_filter to store the search.
        I'm not certain, but I'm pretty sure this value is search backend-
        specific.  Just keep that in mind.

        """
        if isinstance(search_filter, QueryDict):
            self.filter = dict((key, lval) for key, lval in search_filter.iterlists())
        elif isinstance(search_filter, dict):
            self.filter = search_filter
        elif search_filter is not None:
            self.filter = json.loads(search_filter)
        else:
            self.filter = {}

    def get_content(self):
        qs = SearchQuerySet()
        search_fields = {
            'q': 'text',
            'controlling_bodies': 'controlling_body',
            'statuses': 'status',
            'file_types': 'file_type',
        }

        for key, val in self.filter.iteritems():
            if key in search_fields:
                field = search_fields[key]
            else:
                field = key

            if val in ([], {}, '', (), None):
                continue

            if isinstance(val, list):
                for item in val:
                    qs = qs.filter(**{field: item})
            else:
                qs = qs.filter(**{field: val})

        return qs.order_by('order_date')

    def get_changes_to(self, item, datetime):
        if item.model_name == 'legfile':
            return {'Title': item.object.title}, item.order_date
        elif item.model_name == 'legminutes':
            return {'Minutes': str(item.object)}, item.order_date

    def get_last_updated_time(self):
        content = self.get_content()
        return (list(content))[-1].order_date

    def get_updates_since(self, datetime):
        new_content = self.get_content().filter(order_date__gt=datetime).order_by('order_date')
        return new_content

    def get_params(self):
        return {'search_filter': json.dumps(self.filter)}

    def get_label(self):
        label = 'New '

        if 'statuses' in self.filter:
            label += self.filter['statuses'] + ' '

        label += 'legislation'

        if 'q' in self.filter:
            is_plural = (' ' in self.filter['q'])
            label += ' containing the keyword' + ('s' if is_plural else '') + ' "' + self.filter['q'] + '"'

        if 'sponsors' in self.filter:
            label += ' sponsored by ' + ' or '.join(self.filter['sponsors'])

        return label
    
    @property
    def filter_query(self):
        d = {}
        for k,v in self.filter.items():
            if isinstance(v, list):
                d[k] = v[0]
            else:
                d[k] = k
        return urlencode(d)


def register_feeds():
    library.register(NewLegislationFeed, 'newly introduced legislation')
    library.register(LegislationUpdatesFeed, 'updates to a piece of legislation')
    library.register(SearchResultsFeed, 'results of a search query')
    library.register(BookmarkedContentFeed, 'bookmarked content')

register_feeds()

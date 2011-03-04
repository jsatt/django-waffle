from django.contrib.auth.models import AnonymousUser, Group, User

from nose.tools import eq_
from test_utils import RequestFactory, TestCase

from test_app import views
from waffle.middleware import WaffleMiddleware
from waffle.models import Flag


def get():
    request = RequestFactory().get('/foo')
    request.user = AnonymousUser()
    return request


def process_request(request, view):
    response = view(request)
    return WaffleMiddleware().process_response(request, response)

class WaffleTests(TestCase):
    def test_persist_active_flag(self):
        flag = Flag.objects.create(name='myflag', percent='0.1')
        request = get()

        # Flag stays on.
        request.COOKIES['dwf_myflag'] = 'True'
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert 'dwf_myflag' in response.cookies
        eq_('True', response.cookies['dwf_myflag'].value)

    def test_persist_inactive_flag(self):
        flag = Flag.objects.create(name='myflag', percent='99.9')
        request = get()

        # Flag stays off.
        request.COOKIES['dwf_myflag'] = 'False'
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert 'dwf_myflag' in response.cookies
        eq_('False', response.cookies['dwf_myflag'].value)

    def test_no_set_unused_flag(self):
        """An unused flag shouldn't have its cookie reset."""
        request = get()
        request.COOKIES['dwf_unused'] = 'True'
        response = process_request(request, views.flag_in_view)
        assert not 'dwf_unused' in response.cookies

    def test_superuser(self):
        """Test the superuser switch."""
        flag = Flag.objects.create(name='myflag', superusers=True)
        request = get()
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

        superuser = User(username='foo', is_superuser=True)
        request.user = superuser
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

        non_superuser = User(username='bar', is_superuser=False)
        request.user = non_superuser
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_staff(self):
        """Test the staff switch."""
        flag = Flag.objects.create(name='myflag', staff=True)
        request = get()
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

        staff = User(username='foo', is_staff=True)
        request.user = staff
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

        non_staff = User(username='foo', is_staff=False)
        request.user = non_staff
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_user(self):
        """Test the per-user switch."""
        user = User.objects.create(username='foo')
        flag = Flag.objects.create(name='myflag')
        flag.users.add(user)

        request = get()
        request.user = user
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

        request.user = User(username='someone_else')
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_group(self):
        """Test the per-group switch."""
        group = Group.objects.create(name='foo')
        user = User.objects.create(username='bar')
        user.groups.add(group)

        flag = Flag.objects.create(name='myflag')
        flag.groups.add(group)

        request = get()
        request.user = user
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

        request.user = User(username='someone_else')
        request.user.save()
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_authenticated(self):
        """Test the authenticated/anonymous switch."""
        flag = Flag.objects.create(name='myflag', authenticated=True)

        request = get()
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

        request.user = User(username='foo')
        assert request.user.is_authenticated()
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_everyone_on(self):
        """Test the 'everyone' switch on."""
        flag = Flag.objects.create(name='myflag', everyone=True)

        request = get()
        request.COOKIES['dwf_myflag'] = 'False'
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

        request.user = User(username='foo')
        assert request.user.is_authenticated()
        response = process_request(request, views.flag_in_view)
        eq_('on', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_everyone_off(self):
        """Test the 'everyone' switch off."""
        flag = Flag.objects.create(name='myflag', everyone=False,
                                   authenticated=True)

        request = get()
        request.COOKIES['dwf_myflag'] = 'True'
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

        request.user = User(username='foo')
        assert request.user.is_authenticated()
        response = process_request(request, views.flag_in_view)
        eq_('off', response.content)
        assert not 'dwf_myflag' in response.cookies

    def test_percent(self):
        """If you have no cookie, you get a cookie!"""
        flag = Flag.objects.create(name='myflag', percent='50.0')
        request = get()
        response = process_request(request, views.flag_in_view)
        assert 'dwf_myflag' in response.cookies

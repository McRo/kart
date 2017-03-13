# import json
# import time
# from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from django.test import TestCase
from django.core.urlresolvers import reverse

from people.models import Artist

from ..models import StudentApplication


class TestApplicationEndPoint(TestCase):
    """
    Tests concernants le endpoint des Student Application
    """

    def setUp(self):
        self.user = User()
        self.user.first_name = "Andrew"
        self.user.last_name = "Warhola"
        self.user.username = "awarhol"
        self.user.password = "xxx"
        self.user.save()
        # save generate token

        self.artist = Artist(user=self.user, nickname="Andy Warhol")
        self.artist.save()

        self.application = StudentApplication(artist=self.artist)
        self.application.save()

    def tearDown(self):
        pass

    def _get_list(self):
        url = reverse('studentapplication-list')
        return self.client.get(url)

    # Must have an login token : client.get(url_for('ping'), headers=[('X-Something', '42')])
    # Read the doc : http://pytest-flask.readthedocs.io/en/latest/features.html
    # def test_list(self):
    #     """
    #     Test list of applications without authentification
    #     """
    #     response = self._get_list()
    #     self.assertEqual(response.status_code, 200)
    #
    # def test_list_auth(self):
    #     """
    #     Test list of applications with authentification
    #     """
    #     user = authenticate(username=self.user.username, password=self.user.password)
    #     response = self._get_list()
    #     self.assertEqual(response.status_code, 200)
    #
    # def test_list_items_auth(self):
    #     """
    #     Test numbers of applications with authentification
    #     """
    #     user = authenticate(username=self.user.username, password=self.user.password)
    #     response = self._get_list()
    #     data = json.loads(response.content)
    #     self.assertEqual(len(data), 1)

    # def test_json_response(self):
    #     """
    #     Test JSON response
    #     """
    #     response = self._get_list()
    #     self.assertTrue(json.loads(response.content))
    #
    # def test_first_app_default_value(self):
    #     """
    #     Test default value
    #     """
    #     url = reverse('studentapplication-detail', kwargs={'pk': 1})
    #     response = self.client.get(url)
    #     self.assertEqual(response.data['first_time'], True)
    #
    # def test_list_contain_artist(self):
    #     """
    #     Informations tests
    #     """
    #     response = self._get_list()
    #     urlartist = reverse('artist-detail', kwargs={'pk': 1})
    #     self.assertContains(response, urlartist)
    #
    # def test_student_app_sorted_by_date(self):
    #     """
    #     Test app order
    #     """
    #     self.user = User()
    #     self.user.first_name = "Chet"
    #     self.user.last_name = "Backer"
    #     self.user.username = "cbacker"
    #     self.user.save()
    #
    #     self.artist = Artist(user=self.user, nickname="Chet Baker")
    #     self.artist.save()
    #
    #     self.application = StudentApplication(artist=self.artist)
    #     time.sleep(0.1)
    #     self.application.save()
    #
    #     url = reverse('studentapplication-list')
    #     response = self.client.get(url)
    #     self.assertLess(response.data[0]["created_on"], response.data[1]["created_on"])
from django.test import RequestFactory, TestCase

from core.adapters import CustomAccountAdapter


class CustomAccountAdapterTests(TestCase):

    def test_signup_redirects_to_purchase_section(self):
        request = RequestFactory().get("/accounts/signup/")

        redirect_url = CustomAccountAdapter().get_signup_redirect_url(request)

        self.assertEqual(redirect_url, "/#packages")

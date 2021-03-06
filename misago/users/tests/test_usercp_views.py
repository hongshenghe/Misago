from path import Path

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse

from misago.acl.testutils import override_acl
from misago.conf import settings
from misago.core import threadstore

from misago.users.avatars import store
from misago.users.testutils import AuthenticatedUserTestCase


class ChangeForumOptionsTests(AuthenticatedUserTestCase):
    def setUp(self):
        super(ChangeForumOptionsTests, self).setUp()
        self.view_link = reverse('misago:usercp_change_forum_options')

    def test_change_forum_options_get(self):
        """GET to usercp change options view returns 200"""
        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Change forum options', response.content)

    def test_change_forum_options_post(self):
        """POST to usercp change options view returns 302"""
        response = self.client.post(self.view_link, data={
                'timezone': 'Asia/Qatar',
                'is_hiding_presence': '1',
                'limits_private_thread_invites_to': '1',
                'subscribe_to_started_threads': '1',
                'subscribe_to_replied_threads': '1',
            })

        self.assertEqual(response.status_code, 302)

        test_user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(test_user.timezone, 'Asia/Qatar')
        self.assertEqual(test_user.is_hiding_presence, 1)
        self.assertEqual(test_user.limits_private_thread_invites_to, 1)
        self.assertEqual(test_user.subscribe_to_started_threads, 1)
        self.assertEqual(test_user.subscribe_to_replied_threads, 1)


class EditSignatureTests(AuthenticatedUserTestCase):
    def setUp(self):
        super(EditSignatureTests, self).setUp()
        self.view_link = reverse('misago:usercp_edit_signature')

    def test_signature_no_permission(self):
        """edit signature view with no ACL returns 404"""
        override_acl(self.user, {
            'can_have_signature': 0,
        })

        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 404)

    def test_signature_locked(self):
        """locked edit signature view returns 200"""
        override_acl(self.user, {
            'can_have_signature': 1,
        })

        self.user.is_signature_locked = True
        self.user.signature_lock_user_message = 'Your siggy is banned.'
        self.user.save()

        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Your siggy is banned', response.content)

    def test_signature_change(self):
        """GET to usercp change options view returns 200"""
        override_acl(self.user, {
            'can_have_signature': 1,
        })

        self.user.is_signature_locked = False
        self.user.save()

        response = self.client.post(self.view_link,
            data={'signature': 'Hello siggy!'})
        self.assertEqual(response.status_code, 302)

        override_acl(self.user, {
            'can_have_signature': 1,
        })

        response = self.client.get(self.view_link)
        self.assertIn('<p>Hello siggy!</p>', response.content)


class ChangeUsernameTests(AuthenticatedUserTestCase):
    def setUp(self):
        super(ChangeUsernameTests, self).setUp()
        self.view_link = reverse('misago:usercp_change_username')

    def test_change_username_get(self):
        """GET to usercp change username view returns 200"""
        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Change username', response.content)

    def test_change_username_post(self):
        """POST to usercp change username view returns 302"""
        response = self.client.post(self.view_link,
                                    data={'new_username': 'Boberson'})
        self.assertEqual(response.status_code, 302)

        test_user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(test_user.username, 'Boberson')

        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 200)
        self.assertIn(test_user.username, response.content)


class ChangeEmailPasswordTests(AuthenticatedUserTestCase):
    def setUp(self):
        super(ChangeEmailPasswordTests, self).setUp()
        self.view_link = reverse('misago:usercp_change_email_password')

        threadstore.clear()

    def _link_from_mail(self, mail_body):
        for line in mail.outbox[0].body.splitlines():
            if line.strip().startswith('http://testserver/'):
                return line.strip()[len('http://testserver'):]
        raise ValueError("mail body didn't contain link with token")

    def test_change_email_password_get(self):
        """GET to usercp change email/pass view returns 200"""
        response = self.client.get(self.view_link)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Change email or password', response.content)

    def test_change_email(self):
        """POST to usercp change email view returns 302"""
        response = self.client.post(self.view_link,
                                    data={'new_email': 'newmail@test.com',
                                          'current_password': 'Pass.123'})
        self.assertEqual(response.status_code, 302)

        self.assertIn('Confirm changes to', mail.outbox[0].subject)
        confirmation_link = self._link_from_mail(mail.outbox[0].body)

        response = self.client.get(confirmation_link)
        self.assertEqual(response.status_code, 302)

        User = get_user_model()
        User.objects.get(email='newmail@test.com')

    def test_change_password(self):
        """POST to usercp change password view returns 302"""
        response = self.client.post(self.view_link,
                                    data={'new_password': 'newpass123',
                                          'current_password': 'Pass.123'})
        self.assertEqual(response.status_code, 302)

        self.assertIn('Confirm changes to', mail.outbox[0].subject)
        confirmation_link = self._link_from_mail(mail.outbox[0].body)

        response = self.client.get(confirmation_link)
        self.assertEqual(response.status_code, 302)

        User = get_user_model()
        test_user = User.objects.get(pk=self.user.pk)
        self.assertFalse(test_user.check_password('Pass.123'))
        self.assertTrue(test_user.check_password('newpass123'))

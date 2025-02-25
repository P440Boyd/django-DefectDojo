import datetime
import logging

from django_test_migrations.contrib.unittest_case import MigratorTestCase
from django_test_migrations.migrator import Migrator
from django.test import TransactionTestCase
from django.utils import timezone
from unittest import skip

logger = logging.getLogger(__name__)


@skip("Outdated - Any future changes of code should not affect these tests")
class TestEndpointMigrationBroken(TransactionTestCase):
    migrate_from = ('dojo', '0104_endpoint_userinfo_creation')
    migrate_to = ('dojo', '0105_endpoint_host_migration')

    def setUp(self):
        super().setUp()
        self.migrator = Migrator()

        self.old_state = self.migrator.apply_initial_migration(self.migrate_from)

        Endpoint = self.old_state.apps.get_model('dojo', 'Endpoint')
        self.endpoints = {
            'empty': Endpoint.objects.create().pk,
            'empty_host': Endpoint.objects.create(host='').pk,
            'invalid_host': Endpoint.objects.create(host='foo bar').pk,
            'invalid_ip': Endpoint.objects.create(host='127.0.1').pk,
            'invalid_port_high': Endpoint.objects.create(host='127.0.0.1:66666').pk,
            'invalid_port_low': Endpoint.objects.create(host='127.0.0.1:-1').pk,
            'invalid_port_word': Endpoint.objects.create(host='127.0.0.1:port').pk,
            'protocol_mismatch': Endpoint.objects.create(protocol='http', host='https://foo.bar').pk,
            'port_mismatch': Endpoint.objects.create(host='https://foo.bar', port=80).pk,
            'path_mismatch': Endpoint.objects.create(host='https://foo.bar/path1', path='/path1').pk,
            'query_mismatch': Endpoint.objects.create(host='https://foo.bar/?key1=value&key2', query='?key1=value&'
                                                                                                     'key2=None').pk,
            'fragment_mismatch': Endpoint.objects.create(host='https://foo.bar/#fragment', fragment='#fragment').pk,
            'missing_host': Endpoint.objects.create(host='file:///etc/passwd').pk,
        }

    def tearDown(self):
        self.migrator.reset()
        super().tearDown()

    def test_migration_endpoint_broken(self):
        with self.assertLogs('dojo.endpoint.utils', 'ERROR') as cm:
            self.migrator.apply_tested_migration(self.migrate_to)
        self.assertIn('ERROR:dojo.endpoint.utils:It is not possible to migrate database because there is/are {} broken '
                      'endpoint(s). Please check logs.'.format(len(self.endpoints)), cm.output)


@skip("Outdated - Any future changes of code should not affect these tests")
class TestEndpointMigration(MigratorTestCase):
    migrate_from = ('dojo', '0104_endpoint_userinfo_creation')
    migrate_to = ('dojo', '0105_endpoint_host_migration')

    def prepare(self):
        Product_Type = self.old_state.apps.get_model('dojo', 'Product_Type')
        Product = self.old_state.apps.get_model('dojo', 'Product')
        Engagement = self.old_state.apps.get_model('dojo', 'Engagement')
        Test = self.old_state.apps.get_model('dojo', 'Test')
        Finding = self.old_state.apps.get_model('dojo', 'Finding')
        Endpoint = self.old_state.apps.get_model('dojo', 'Endpoint')
        Endpoint_Status = self.old_state.apps.get_model('dojo', 'Endpoint_Status')
        self.endpoints = {
            'valid_host': Endpoint.objects.create(host='foo.bar').pk,
            'valid_ip': Endpoint.objects.create(host='127.0.0.1').pk,
            'host_port': Endpoint.objects.create(host='foo.bar:22').pk,
            'ip_port': Endpoint.objects.create(host='127.0.0.1:22').pk,
            'url': Endpoint.objects.create(host='http://foo.bar/').pk,
            'url_existing_port': Endpoint.objects.create(host='https://foo.bar:4433/', port=4433).pk,
            'full_url': Endpoint.objects.create(host='https://alice@foo.bar:4433/path1/path2/?key1=value1&no_value_key'
                                                     '#fragmentX').pk,
            'path_with_slash': Endpoint.objects.create(host='bar.foo', path='/test').pk,
        }

        self.prod_type = Product_Type.objects.create()
        self.product = Product.objects.create(prod_type=self.prod_type)
        self.engagement = Engagement.objects.create(
            product=self.product,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc)
        )
        self.test = Test.objects.create(
            engagement_id=self.engagement.pk,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc),
            test_type_id=1
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.finding = Finding.objects.create(test=self.test, reporter_id=User.objects.create().pk).pk
        self.endpoints_eps = {
            'short': Endpoint.objects.create(protocol='http', host='foo.bar.eps', product=self.product).pk,
            'long': Endpoint.objects.create(protocol='http', host='foo.bar.eps', port=80, product=self.product).pk,
        }
        self.endpoint_status = {
            'old': Endpoint_Status.objects.create(
                last_modified=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=self.finding,
                endpoint_id=self.endpoints_eps['short']
            ).pk,
            'new': Endpoint_Status.objects.create(
                last_modified=datetime.datetime(2021, 1, 1, tzinfo=timezone.utc),
                mitigated=False,
                finding_id=self.finding,
                endpoint_id=self.endpoints_eps['long']
            ).pk,
        }

    def test_migration_endpoint(self):
        Endpoint = self.new_state.apps.get_model('dojo', 'Endpoint')
        Endpoint_Status = self.new_state.apps.get_model('dojo', 'Endpoint_Status')

        endpoint = Endpoint.objects.get(pk=self.endpoints['valid_host'])
        self.assertEqual(endpoint.host, 'foo.bar')

        endpoint = Endpoint.objects.get(pk=self.endpoints['valid_ip'])
        self.assertEqual(endpoint.host, '127.0.0.1')

        endpoint = Endpoint.objects.get(pk=self.endpoints['host_port'])
        self.assertEqual(endpoint.host, 'foo.bar')
        self.assertEqual(endpoint.port, 22)

        endpoint = Endpoint.objects.get(pk=self.endpoints['ip_port'])
        self.assertEqual(endpoint.host, '127.0.0.1')
        self.assertEqual(endpoint.port, 22)

        endpoint = Endpoint.objects.get(pk=self.endpoints['url'])
        self.assertEqual(endpoint.protocol, 'http')
        self.assertEqual(endpoint.host, 'foo.bar')
        self.assertEqual(endpoint.port, 80)
        self.assertIsNone(endpoint.path)

        endpoint = Endpoint.objects.get(pk=self.endpoints['url_existing_port'])
        self.assertEqual(endpoint.port, 4433)

        endpoint = Endpoint.objects.get(pk=self.endpoints['full_url'])
        self.assertEqual(endpoint.protocol, 'https')
        self.assertEqual(endpoint.userinfo, 'alice')
        self.assertEqual(endpoint.host, 'foo.bar')
        self.assertEqual(endpoint.port, 4433)
        self.assertEqual(endpoint.path, 'path1/path2/')
        self.assertEqual(endpoint.query, 'key1=value1&no_value_key')
        self.assertEqual(endpoint.fragment, 'fragmentX')

        endpoint = Endpoint.objects.get(pk=self.endpoints['path_with_slash'])
        self.assertEqual(endpoint.path, 'test')

        low_id = Endpoint.objects.filter(id=min(self.endpoints_eps.values()))
        logger.debug("Low id: {}".format(list(low_id)))
        self.assertEqual(low_id.count(), 1)
        high_id = Endpoint.objects.filter(id=max(self.endpoints_eps.values()))
        logger.debug("High id: {}".format(list(high_id)))
        self.assertEqual(high_id.count(), 0)

        eps = Endpoint_Status.objects.filter(
            finding_id=self.finding,
            endpoint_id__in=self.endpoints_eps.values()
        )
        self.assertEqual(eps.count(), 1)
        self.assertFalse(eps[0].mitigated)


# TODO: These tests can be skipped in 2.11.x or later
# @skip("Outdated - Any future changes of code should not affect these tests")
class TestEndpointStatusMigration(MigratorTestCase):
    migrate_from = ('dojo', '0149_harmonize_user_format')
    migrate_to = ('dojo', '0151_index_endpoint_status')

    def prepare(self):
        Product_Type = self.old_state.apps.get_model('dojo', 'Product_Type')
        Product = self.old_state.apps.get_model('dojo', 'Product')
        Engagement = self.old_state.apps.get_model('dojo', 'Engagement')
        Test = self.old_state.apps.get_model('dojo', 'Test')
        Finding = self.old_state.apps.get_model('dojo', 'Finding')
        Endpoint = self.old_state.apps.get_model('dojo', 'Endpoint')
        Endpoint_Status = self.old_state.apps.get_model('dojo', 'Endpoint_Status')

        self.prod_type = Product_Type.objects.create()
        self.product = Product.objects.create(prod_type=self.prod_type)
        self.engagement = Engagement.objects.create(
            product=self.product,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc)
        )
        self.test = Test.objects.create(
            engagement_id=self.engagement.pk,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc),
            test_type_id=1
        )
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create().pk
        self.finding = Finding.objects.create(test=self.test, reporter_id=user).pk
        self.endpoint = Endpoint.objects.create(protocol='http', host='foo.bar.eps', product=self.product).pk
        self.endpoint_status = {
            'second': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 3, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 4, 1, tzinfo=timezone.utc),
                mitigated=False,
                finding_id=self.finding,
                endpoint_id=self.endpoint
            ).pk,
            'first': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 1, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 1, 1, tzinfo=timezone.utc),
                mitigated=False,
                finding_id=self.finding,
                endpoint_id=self.endpoint
            ).pk,
            'last_modified': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=self.finding,
                endpoint_id=self.endpoint
            ).pk,
            'empty_endpoint_1': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=self.finding,
                endpoint_id=None
            ).pk,
            'empty_endpoint_2': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=self.finding,
                endpoint_id=None
            ).pk,
            'empty_finding_1': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=None,
                endpoint_id=self.endpoint
            ).pk,
            'empty_finding_2': Endpoint_Status.objects.create(
                date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
                last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
                mitigated=True,
                finding_id=None,
                endpoint_id=self.endpoint
            ).pk,
        }

        self.another_finding = Finding.objects.create(test=self.test, reporter_id=user).pk
        self.another_endpoint = Endpoint.objects.create(protocol='http', host='bar.foo.eps', product=self.product).pk
        self.another_endpoint_status = Endpoint_Status.objects.create(
            date=datetime.datetime(2021, 2, 1, tzinfo=timezone.utc),
            last_modified=datetime.datetime(2021, 5, 1, tzinfo=timezone.utc),
            mitigated=True,
            finding_id=self.another_finding,
            endpoint_id=self.another_endpoint
        ).pk

    def test_migration_endpoint(self):
        Endpoint = self.new_state.apps.get_model('dojo', 'Endpoint')
        Endpoint_Status = self.new_state.apps.get_model('dojo', 'Endpoint_Status')

        with self.subTest("Standard usecase"):
            eps = Endpoint_Status.objects.filter(
                finding_id=self.finding,
                endpoint_id=self.endpoint
            )
            self.assertEqual(eps.count(), 1)
            self.assertTrue(eps[0].mitigated)
            self.assertEqual(eps[0].date, datetime.datetime(2021, 1, 1, tzinfo=timezone.utc))
            self.assertEqual(eps[0].last_modified, datetime.datetime(2021, 5, 1, tzinfo=timezone.utc))

            eps = Endpoint_Status.objects.filter(pk=self.another_endpoint_status)
            self.assertEqual(eps.count(), 1)

        with self.subTest("Broken endpoint_statuses"):
            eps = Endpoint_Status.objects.filter(endpoint_id=None, finding_id=self.finding)
            self.assertEqual(eps.count(), 2)

            eps = Endpoint_Status.objects.filter(endpoint_id=self.endpoint, finding_id=None)
            self.assertEqual(eps.count(), 2)


# TODO: These tests can be skipped in 2.10.x or later
# @skip("Outdated - Any future changes of code should not affect these tests")
class TestRemoveEndpointMitigatedMigration(MigratorTestCase):
    migrate_from = ('dojo', '0152_notifications_template')
    migrate_to = ('dojo', '0153_migrate_endpoint_mitigated')

    def prepare(self):
        Product_Type = self.old_state.apps.get_model('dojo', 'Product_Type')
        Product = self.old_state.apps.get_model('dojo', 'Product')
        Engagement = self.old_state.apps.get_model('dojo', 'Engagement')
        Test = self.old_state.apps.get_model('dojo', 'Test')
        Finding = self.old_state.apps.get_model('dojo', 'Finding')
        Endpoint = self.old_state.apps.get_model('dojo', 'Endpoint')
        Endpoint_Status = self.old_state.apps.get_model('dojo', 'Endpoint_Status')
        Dojo_User = self.old_state.apps.get_model('dojo', 'Dojo_User')

        self.prod_type = Product_Type.objects.create()
        self.product = Product.objects.create(prod_type=self.prod_type)
        self.engagement = Engagement.objects.create(
            product=self.product,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc)
        )
        self.test = Test.objects.create(
            engagement_id=self.engagement.pk,
            target_start=datetime.datetime(2020, 1, 1, tzinfo=timezone.utc),
            target_end=datetime.datetime(2022, 1, 1, tzinfo=timezone.utc),
            test_type_id=1
        )

        self.users = {
            '1': Dojo_User.objects.create(username='alice').pk,
            '2': Dojo_User.objects.create(username='bob').pk,
        }
        self.findings = {
            '1': Finding.objects.create(test=self.test, reporter_id=self.users['1']).pk,
            '2': Finding.objects.create(test=self.test, reporter_id=self.users['2']).pk,
        }
        self.endpoints = {
            'nomit': Endpoint.objects.create(protocol='http', host='foo.bar.eps', product=self.product,
                                             mitigated=False).pk,
            'mit': Endpoint.objects.create(protocol='http', host='bar.foo.eps', product=self.product,
                                           mitigated=True).pk,
        }
        self.endpoint_status = {
            'nomit_nomit_f1': Endpoint_Status.objects.create(
                endpoint_id=self.endpoints['nomit'],
                mitigated=False,
                finding_id=self.findings['1'],
            ).pk,
            'nomit_mit1_f2': Endpoint_Status.objects.create(
                endpoint_id=self.endpoints['nomit'],
                mitigated=True,
                mitigated_by_id=self.users['1'],
                finding_id=self.findings['2'],
            ).pk,
            'mit_mit2_f1': Endpoint_Status.objects.create(
                endpoint_id=self.endpoints['mit'],
                mitigated=True,
                mitigated_by_id=self.users['2'],
                finding_id=self.findings['1'],
            ).pk,
            'mit_nomit_f2': Endpoint_Status.objects.create(
                endpoint_id=self.endpoints['mit'],
                mitigated=False,
                finding_id=self.findings['2'],
            ).pk,
        }

    def test_migration_endpoint_mitigated(self):
        Endpoint_Status = self.new_state.apps.get_model('dojo', 'Endpoint_Status')

        eps = Endpoint_Status.objects.get(pk=self.endpoint_status['nomit_nomit_f1'])
        self.assertFalse(eps.mitigated)
        self.assertIsNone(eps.mitigated_by)

        eps = Endpoint_Status.objects.get(pk=self.endpoint_status['nomit_mit1_f2'])
        self.assertTrue(eps.mitigated)
        self.assertEqual(eps.mitigated_by_id, self.users['1'])

        eps = Endpoint_Status.objects.get(pk=self.endpoint_status['mit_mit2_f1'])
        self.assertTrue(eps.mitigated)
        self.assertEqual(eps.mitigated_by_id, self.users['2'])

        eps = Endpoint_Status.objects.get(pk=self.endpoint_status['mit_nomit_f2'])
        self.assertTrue(eps.mitigated)
        self.assertEqual(eps.mitigated_by_id, self.users['2'])

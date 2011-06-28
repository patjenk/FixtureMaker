from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import connections, router, DEFAULT_DB_ALIAS
from fk_fixture_maker.utils import FixtureMaker, get_foreign_keys
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures.'),
        make_option('--indent', default=None, dest='indent', type='int',
            help='Specifies the indent level to use when pretty-printing output'),
        make_option('-d', '--max-depth', default='0', action='store', dest='max_depth',
            help='The maximum depth for which the current data should be dumped.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to load '
                'fixtures into. Defaults to the "default" database.'),
        make_option('--id', action='append', dest='object_ids', default=[],
            help='Output object with specified id (use multiple --id to specify multiple objects).'),
        make_option('-e', '--exclude', dest='exclude',action='append', default=[],
            help='appname.ModelName to exclude (use multiple --exclude to exclude multiple apps).'),
    )
    help = ("Ouput the contents of the specified object and it's dependencies "
            "as a fixture of the given format.")
    args = 'appname.ModelName'
  
    def handle(self, app_label=None, **options):
        from django.db.models import get_app, get_apps, get_models, get_model

        format = options.get('format','json')
        indent = options.get('indent',None)
        using = options.get('database', DEFAULT_DB_ALIAS)
        max_depth = int(options.get('max_depth', 0))
        connection = connections[using]
        exclude = options.get('exclude',[])
        object_ids = options.get('object_ids', [])
        show_traceback = options.get('traceback', False)

        excluded_models = [] 
        for excluded_name in exclude:
            excluded_app_name, excluded_model_name = excluded_name.split('.')
            try:
                excluded_app = get_app(excluded_app_name)
            except ImproperlyConfigured:
                raise CommandError("Unknown application: %s" % excluded_app_name)
            excluded_model = get_model(excluded_app_name, excluded_model_name)
            if excluded_model is None:
                raise CommandError("Unknown model: %s.%s" % (excluded_app_name, excluded_model_name))
            excluded_models.append(excluded_model)  

        if not app_label:
            raise CommandError("No application specified")
        app_name, model_name = app_label.split('.')
        try:
            app = get_app(app_name)
        except ImproperlyConfigured:
            raise CommandError("Unknown application: %s" % app_name)
        model = get_model(app_name, model_name)
        if model is None:
            raise CommandError("Unknown model: %s.%s" % (app_name, model_name))

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            raise CommandError("Unknown serialization format: %s" % format)

        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)

        # Now collate the objects to be serialized.
        objects = []
        if not model._meta.proxy and router.allow_syncdb(using, model):
            if len(object_ids) > 0:
                objects.extend(model._default_manager.using(using).filter(id__in=object_ids))
            else:
                objects.extend(model._default_manager.using(using).all())

        objects.extend(get_foreign_keys(objects=objects, max_depth=max_depth-1, excluded_models=excluded_models))

        try:
            return serializers.serialize(format, objects, indent=indent)
        except Exception, e:
            raise
            if show_traceback:
                raise
            raise CommandError("Unable to serialize database: %s" % e)

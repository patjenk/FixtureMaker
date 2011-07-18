from django.core import serializers
from django.db import models

class FixtureMaker:
  """This Ouputs json fixtures for a given queryset following all foreign key relationships, requires a QuerySet
  object and a folder called fixture_maker in the same directory as manage.py"""

  def __init__(self, queryset):
    if not isinstance(queryset, models.query.QuerySet):
      print 'Please pass a QuerySet instance'
      return
    opts = queryset[0]._meta
    # This is updated for each fk depth
    self.fk_dict = [[{
                    'field': None,
                    'name': opts.object_name,
                    'model': queryset.model,
                    'parent': None,
                    'relationship': 'root',
                    'values': queryset,
                    }]]
    connections = self.__get_all_foreign_fields_and_data(opts, queryset)
    self.fk_dict.append(connections)
    connections_to_follow_list = self.__check_for_connections(connections)
    if connections_to_follow_list:
      self.__get_connections(connections_to_follow_list)
    else:
      self.__save_fixtures(self.fk_dict)


  def __get_connections(self, connections_to_follow_list):
    """This gets connections from each depth of Foreign Keys. Takes in a Connections list and loops through until
    there are no more foreign keys with values.  When all fk's are followed to their end it calls
    __save_fixtures()"""
    fk_fields = []
    for model_dict in connections_to_follow_list:
      opts = model_dict['values'][0]._meta
      tmp_fk_fields = self.__get_all_foreign_fields_and_data(opts, model_dict['values'])
      if tmp_fk_fields:
        fk_fields.extend(tmp_fk_fields)

    self.fk_dict.append(fk_fields)
    connections_to_follow = self.__check_for_connections(fk_fields)
    if connections_to_follow:
      self.__get_connections(connections_to_follow)
    else:
      self.__save_fixtures(self.fk_dict)


  def __get_all_foreign_fields_and_data(self, opts, queryset):
    """This gets all foreign fields for a give opts.  It then goes through the specified queryset and gets all
    data from those foreign fields, formats it and saves it to our output"""
    connections = []
    # Get ForeignKey Fields
    for field in opts.fields:
      if field.get_internal_type() == 'ForeignKey':
        # If we have the parent and have the base get the values for the base
        values_needed = queryset.values_list(field.name, flat=True)
        # I filtered out None values because I had a problem querying one of the models using None values
        not_none_values = [id for id in values_needed if id != None]
        child_queryset = []
        if not_none_values:
          child_queryset = field.related.parent_model.objects.filter(pk__in=not_none_values)
        tmp_dict = self.__build_dict_using_field(opts, field, child_queryset)
        connections.append(tmp_dict)
    # Get m2m fields
    m2m_fields = opts.many_to_many
    if m2m_fields:
      for field in m2m_fields:
        tmp_dict = self.__build_dict_using_field(opts, field)
        for item in queryset:
          values = getattr(item, field.name).all()
          if values:
            for value in values:
              tmp_dict['values'].append(value)
        if tmp_dict['values']:
          # Make sure we don't have duplicates
          tmp_dict['values'] = [x for x in set(tmp_dict['values'])]
        connections.append(tmp_dict)
    return connections


  def __build_dict_using_field(self, opts, field, values_queryset=None,):
    """Takes in a field and makes a tmp_dict the way we like it.  If it is a many_to_many releationship we leave
    values empty at first, (denoted by values_queryset)"""
    tmp_dict = {
                'field': field.name,
                'name': field.related.parent_model._meta.object_name,
                'model': field.related.parent_model,
                'parent': opts.object_name,
               }
    if values_queryset != None:
      tmp_dict['relationship'] = 'ForeignKey'
      tmp_dict['values'] = values_queryset
    else:
      tmp_dict['relationship'] = 'ManyToMany'
      tmp_dict['values'] = []
    return tmp_dict


  def __check_for_connections(self, connections):
    """Loops through all connections and verifies that we need to go into more Foreign Keys, returns True
    if we do False if we don't"""
    tmp_list = []
    for model_dict in connections:
      if model_dict['values']:
        tmp_list.append(model_dict)
    return tmp_list


  def __save_fixtures(self, all_connections):
    """Takes a properly formatted list, and makes a seperate fixture file for each different model in the list"""
    #omg loop through first, cause i'm a noob, and seperate data based on model
    model_data_dict = {}
    for depth in all_connections:
      for model_dict in depth:
        if model_dict['values']:
          try:
            model_data_dict[model_dict['name']] = model_dict['values']
          except KeyError:
            model_data_dict[model_dict['name']].extend(model_dict['values'])
    for model_name, model_values in model_data_dict.items():
      try:
        f = open('fixture_maker/%s_fixture.json' % (model_name.lower()), 'w')
        print 'Creating Fixture for %s, with %s items' % (model_name, len(model_values))
        serializers.serialize('json', model_values, stream=f, indent=2)
        f.close()
      except IOError:
        print 'If you see this you most likely have to create a directory called \'fixture_maker\' in the same directory manage.py is in'
        return

def get_foreign_keys(objects, max_depth=1, excluded_models=[]):
  """
  Determine all foreign fields in a list of objects and return the objects.
  """
  result = set() 
  if max_depth < 0:
    return result
  if len(objects) == 0:
    return result
  for object in objects:
    for field in object._meta.fields:
      if field.get_internal_type() == 'ForeignKey' and not field.related.parent_model in excluded_models and None != getattr(object, field.name):
        result.update(field.related.parent_model.objects.filter(pk=getattr(object, field.name).id))
    m2m_fields = object._meta.many_to_many
    if m2m_fields:
      for field in m2m_fields:
        if not field.related.parent_model in excluded_models:
          result.update(getattr(object,field.name).all())
  result.update(get_foreign_keys(objects=result, max_depth=max_depth-1, excluded_models=excluded_models))
  return result

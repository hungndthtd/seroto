{
  'name': 'Seroto Course Event',
  'version': '1.0',
  'depends': [
    'event',
    'website_event',
    'website_event_sale',
  ],
  'data': [
    'security/ir.model.access.csv',
    'views/course_event_type_views.xml',
    'views/course_event_views.xml',
    'templates/website_event_templates.xml',
    # 'templates/homepage_event.xml',
    'templates/event_card.xml',
  ],
  'assets': {
    # 'web.assets_frontend_lazy': [
    #   'seroto_course_event/static/src/js/event_register_modal.js',
    # ],
    'web.assets_frontend': [
      'seroto_course_event/static/src/scss/course_event.scss',
      # 'seroto_course_event/static/src/js/event_register_modal.js',
    ]
  },
  'installable': True
}
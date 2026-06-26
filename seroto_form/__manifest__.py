{
  'name': 'Seroto Form',
  'version': '1.0',
  'author': 'Seroto',
  'depends': [
    'website',
    'website_crm',
    'crm',
    'mail'
  ],
  'data': [
    # 'views/course_modal.xml',
    'views/templates.xml',
  ],
  'assets': {
    'web.assets_frontend': [
      'seroto_form/static/src/js/register_modal.js',
      'seroto_form/static/src/css/style.css'
    ]
  },
  'installable': True
}
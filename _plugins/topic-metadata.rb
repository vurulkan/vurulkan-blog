# Keep generated category metadata aligned with the visible topic introduction.
Jekyll::Hooks.register :pages, :pre_render do |page|
  next unless page.data['layout'] == 'category'

  description = page.site.data.fetch('topic_descriptions', {})[page.data['title']]
  page.data['description'] = description if description
end

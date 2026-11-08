# Keep generated category metadata aligned with the visible topic introduction.
Jekyll::Hooks.register :pages, :pre_render do |page|
  next unless page.data['layout'] == 'category'

  title = page.data['title'] || page.title
  description = page.site.data.fetch('topic_descriptions', {})[title]
  page.data['description'] = description if description
end

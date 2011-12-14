# -*- coding: utf-8 -*-
#
# Copyright 2008 Optaros, Inc.
#
# @todo: Refactor this code in order to make it more easy to read! 

import re
from urlparse import urlsplit

from trac.core import *
from trac.web.api import IRequestFilter
from trac.web.chrome import add_script, add_stylesheet,ITemplateProvider
from trac.config import ListOption, BoolOption
from trac.util.html import html
from trac.util.compat import sorted

class MenuManagerModule(Component):
    implements(IRequestFilter, ITemplateProvider)

    managed_menus = ListOption('menu-custom', 'managed_menus', 'mainnav,metanav', 
                        doc="""List of menus to be controlled by the Menu Manager""")
    serve_ui_files = BoolOption('menu-custom', 'serve_ui_files', True)

    # ITemplateProvider
    def get_templates_dirs(self):
        return []
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tracmenus',resource_filename(__name__, 'htdocs'))]
   
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler
    def post_process_request(self, req, template, data, content_type):
        if 'nav_orig' in req.chrome: 
            return template, data, content_type
        req.chrome['nav_orig'] = req.chrome['nav'].copy()
        if 'ctxtnav' in self.managed_menus and 'ctxtnav' in req.chrome:
            req.chrome['nav_orig']['ctxtnav']=[dict(name='ctxtnav_'+str(idx), label=ctx_label) 
                                               for idx, ctx_label in enumerate(req.chrome['ctxtnav'])]
        for menu_name in self.managed_menus:
            req.chrome['nav'][menu_name] = self._get_menu(req, menu_name, req.chrome['nav_orig'])    
            if menu_name=='ctxtnav':
                req.chrome['ctxtnav'] = [ ctxt_item.get('label') for ctxt_item in req.chrome['nav'][menu_name] ]
        
        if self.serve_ui_files:
            add_script(req, 'tracmenus/js/superfish.js')
            add_script(req, 'tracmenus/js/tracmenus.js')
            add_script(req, 'tracmenus/js/jquery.hoverIntent.minified.js')
            add_stylesheet(req, 'tracmenus/css/tracmenus.css')
        return template, data, content_type
        
    def _get_menu(self, req, menu_name, nav_orig):
        config_menu, config_options = self._get_config_menus(req, menu_name)
        menu_orig = nav_orig.get(menu_name, [])
        hide_if_no_children = []
        menu_result = []
        
        if 'inherit' in config_options:
            menu_orig += nav_orig.get(config_options['inherit'], [])
            
        tree_menu={} 
        for option in sorted(menu_orig+[{'name':key} for key in config_menu.keys()], 
                             key=lambda x:int(config_menu.get(x['name'],{}).get('order',999))):            
            name = option['name']
            if 'visited' in tree_menu.get(name, []) \
                    or (config_menu.get(name, {}).get('enabled', True)==False and not 'active' in option)\
                    or config_menu.get(name, {}).get('if_path_info', True)==False \
                    or False in [req.perm.has_permission(perm) for perm in config_menu.get(name, {}).get('perm', [])]:
                continue
            
            tree_node = tree_menu.setdefault(name, {})
            tree_node.update(option.copy())
            
            if 'label' in option and 'label' in config_menu.get(name, []):
                del config_menu[name]['label']
            tree_node.update(config_menu.get(name, {'parent_name':'unassigned'}))
            
            if tree_node.get('hide_if_no_children'):
                hide_if_no_children.append(tree_node)
            
            tree_node['label'] = html(tree_node.setdefault('label', html.a(name)))
            tree_node['visited'] = True 
            if tree_node.get('href'):
                tree_node_href = urlsplit(tree_node['href'])
                tree_node.setdefault('active', tree_node_href[2]==req.path_info and tree_node_href[3] in req.environ['QUERY_STRING'])   

            if '_tmp_children' in tree_node:
                tree_node['children'] = html.ul()
                tree_node['label'].append(tree_node['children'])
                tree_node['children'].children.extend(tree_node['_tmp_children'])
                del tree_node['_tmp_children']
                        
            if (tree_node['parent_name']=='unassigned' and not 'unassigned' in config_menu) \
                    or tree_node['parent_name']=='top': 
                menu_result.append(tree_node)
                continue

            tree_node['parent'] = tree_menu.setdefault(tree_node['parent_name'], {})

            child_node = html.li(class_=tree_node.get('active')==True and 'active' or None)
            tree_node['outter_html'] = child_node 
            child_node.children=[tree_node['label']]
            if 'label' in tree_node['parent']:
                if not 'children' in tree_node['parent']:
                    tree_node['parent']['children'] = html.ul()
                    tree_node['parent']['label'].append(tree_node['parent']['children'])
                tree_node['parent']['children'].append(child_node)
            else:
                tree_node['parent'].setdefault('_tmp_children',[]).append(child_node)
        
        for hide_node in hide_if_no_children:
            if not hide_node.get('children'):
                if hide_node['parent_name']=='top':
                    pos = menu_result.index(hide_node)
                    del menu_result[pos]
                else:    
                    pos = hide_node['parent']['children'].children.index(hide_node['outter_html'])
                    del hide_node['parent']['children'].children[pos]
        return menu_result

    def _get_config_menus(self, req, menu_name):
        new_menu_option=lambda name: dict(name=name, href='#', enabled=False, parent_name='top')
        menu, options = {}, {}
        for option, value in self.config[menu_name].options():
            item_parts = option.split('.',1)
            name, prop_name = item_parts[0], len(item_parts)>1 and item_parts[1] or 'enabled'
            if name in ['inherit']:
                options[name] = value
                continue
            menu.setdefault(name, new_menu_option(name)) 
            if prop_name=='parent':
                menu[name]['parent_name']=value
                continue
            elif prop_name=='enabled':
                value=self.config[menu_name].getbool(option, True)
            elif prop_name=='href':
                value = value.replace('$PATH_INFO', req.path_info)
                menu[name]['label']=menu[name].setdefault('label', html.a())(href=value.startswith('/') and req.href().rstrip('/') and value or value)
            elif prop_name=='label':
                menu[name].setdefault('label', html.a(href='#'))(value)
                continue
            elif prop_name=='path_info':
                menu[name]['if_path_info'] = re.match(value, req.path_info) and True or False
            elif prop_name=='enabled':
                menu[name][prop_name] = self.config[menu_name].getbool(option, False)
                continue
            elif prop_name=='hide_if_no_children':
                menu[name][prop_name] = self.config[menu_name].getbool(option, False)
                continue
            elif prop_name=='perm':
                menu[name][prop_name] = self.config[menu_name].getlist(option, default=[], sep=',')
                continue
            menu[name][prop_name]=value
        return menu, options

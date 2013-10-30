# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.contrib import admin
from lizard_ui.urls import debugmode_urlpatterns
from django.contrib.auth.decorators import login_required

from lizard_ocean import views

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$',
        views.MainView.as_view(),
        name='ocean_main'),
    url(r'^netcdf/$',
        login_required(views.RawNetcdfView.as_view()),
        name='ocean_netcdf'),
    url(r'^ejwms/$',
        views.WmsView.as_view(),
        name='ejwms'),
    url(r'^ejrastersetinfo/$',
        views.RastersetInfoView.as_view(),
        name='ejrastersetinfo'),
    url(r'^ejclick/$',
        views.MapClickView.as_view(),
        name='ejclick'),
    url(r'^ejflot/$',
        views.GraphView.as_view(format='flot'),
        name='ejflot'),
    url(r'^ejimg/$',
        views.GraphView.as_view(format='png'),
        name='ejimg'),
    url(r'^ejdownload/$',
        views.DownloadView.as_view(),
        name='ejdownload'),
    url(r'^ejlegendinfo/$',
        views.LegendInfoView.as_view(),
        name='ejlegendinfo'),
    url(r'^ejlegend/$',
        views.LegendView.as_view(),
        name='ejlegend'),
    url(r'^ui/', include('lizard_ui.urls')),
    # url(r'^map/', include('lizard_map.urls')),
    url(r'^admin/', include(admin.site.urls)),
    # url(r'^something/',
    #     views.some_method,
    #     name="name_it"),
    )
urlpatterns += debugmode_urlpatterns()

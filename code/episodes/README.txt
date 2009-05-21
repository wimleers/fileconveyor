$Id$

Description
-----------

Episodes is a module that includes the identically named Episodes [1]
framework in Drupal. Episodes allows you to measure episodes in a web page's
loading sequence. Hence its name.

It works by embedding some JavaScript code in the web page. This code then
measures how long the different episodes take to load. Finally, the results
are sent back to a web server (logged through Apache). This can be a different
server than the one Drupal runs on.
Because it's JavaScript, it's run in actual browsers, which means the results
give you an accurate representation of the real-world page loading performance
of your web pages. It's not perfect, amongst others because you cannot
accurately measure time through JavaScript, but give or take a few
milliseconds, it's accurate. And that's what we really need.

This module provides easy integration with Drupal. It automatically creates an
episode for each JavaScript behavior defined in Drupal.behaviors. You can
disable Episodes for specific behaviors or on certain paths. Basic reports
(with charts!) are also provided (e.g. average page load time per day for the
last month).

Episodes (the JavaScript, thus also this Drupal module) is designed to run on
production web sites. Otherwise the measurements wouldn't be based on
real-world circumstances and would therefor be inaccurate or even meaningless.
So it's meant to be a continuous performance monitoring tool. So it's not
unlike Google Analytics in the way it's mean to be used

The goal of this framework is to become an industry standard. And it's likely
that it'll manage to do just that, because the author and driving force behind
it is Steve Souders himself. Drupal is the first CMF/CMS to support it.

This module was written as part of the bachelor thesis [2] of Wim Leers at
Hasselt University [3].

[1] http://stevesouders.com/episodes/
[2] http://wimleers.com/tags/bachelor-thesis
[3] http://uhasselt.be/


Dependencies
------------
- Hierarchical Select
- Hierarchical Select Flat List


Installation
------------
1) Place this module directory in your "modules" folder (this will usually be
   "sites/all/modules/"). Don't install your module in Drupal core's "modules"
   folder, since that will cause problems and is bad practice in general. If
   "sites/all/modules" doesn't exist yet, just create it.

2) Enable the module.

3) Visit "admin/settings/episodes" to learn about the various settings. If
   you're using an external logging service, you can configure it here.

4) Visit "admin/settings/episodes/behaviors" if you want to ignore some Drupal
   behaviors in your episodes. By default, each Drupal behavior is included as
   an episode.

5) Install the Firebug add-on. You will already be able to see the episodes in
   there! (See the Firebug add-on section.)

6) A couple of the measurements cannot be configured without altering some
   code. These are the measurements for the <head> tag and at the bottom of
   the page. See the "Additional measurements" section. Optional of course.

7) If you want to use the included analysis tools, continue, otherwise you're
   ready!

8) We want Apache's logging to do the heavy logging work for us. That's why
   you'll have to edit your httpd.conf. Look at
     extra/episodes.httpd.conf
   for detailed instructions.


Firebug add-on
--------------
A Firebug add-on that displays the measured episodes on the current page is
available from http://stevesouders.com/episodes/addon.php.
When a web page does not include the episodes JS framework, the Firebug add-on
will still measure some basic episodes (backend, frontend, totaltime).


Additional measurements: css, headerjs, footerjs
------------------------------------------------
It's possible to perform additional measurements but it requires that you
alter the page.tpl.php file of your theme.
All you have to do is change this:

    <?php print $styles ?>
    <?php print $scripts ?>
to:
    <?php if (episodes_is_enabled()): ?><script type="text/javascript">window.postMessage("EPISODES:mark:css", document.location);</script><? endif; ?>
    <?php print $styles ?>
    <?php if (episodes_is_enabled()): ?><script type="text/javascript">window.postMessage("EPISODES:measure:css", document.location);window.postMessage("EPISODES:mark:headerjs", document.location);</script><? endif; ?>
    <?php print $scripts ?>
    <?php if (episodes_is_enabled()): ?><script type="text/javascript">window.postMessage("EPISODES:measure:headerjs", document.location);</script><? endif; ?>

And:
    <?php print $closure ?>
to:
    <?php if (episodes_is_enabled() && strlen(drupal_get_js('footer'))): ?><script type="text/javascript">window.postMessage("EPISODES:mark:footerjs", document.location);</script><? endif; ?>
    <?php print $closure ?>
    <?php if (episodes_is_enabled() && strlen(drupal_get_js('footer'))): ?><script type="text/javascript">window.postMessage("EPISODES:measure:footerjs", document.location);</script><? endif; ?>

Really, that's all there is to it!


Credit
------
- episodes.js from Steve Souders in a heavily changed form. Also
  episodes-compat.js but in an unchanged form.
  http://stevesouders.com/episodes/
- Browser.php from Chris Schuld
  http://chrisschuld.com/projects/browser-php-detecting-a-users-browser-from-php
- episodes.httpd.conf is based on Jiffy's jiffy.httpd.conf, but is different
  in several ways. Thanks to that, I was able to copy some of their regular
  expressions.
  http://code.google.com/p/jiffy-web/source/browse/trunk/ingestor/jiffy.httpd.conf


Author
------
Wim Leers ~ http://wimleers.com/

This application was written as part of the bachelor thesis of Wim Leers at
Hasselt University.

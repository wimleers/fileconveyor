$Id$

Description
-----------



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


Additional measurements: episodes, css, headerjs, footerjs
----------------------------------------------------------
It's possible to perform additional measurements but it requires that you
alter the page.tpl.php file of your theme.
All you have to do is change this:

    <?php print $head ?>
    <?php print $styles ?>
    <?php print $scripts ?>
to:
    <?php if (episodes_is_enabled()): ?><script type="text/javascript">window.postMessage("EPISODES:mark:episodes", document.location);</script><? endif; ?>
    <?php print $head ?>
    <?php if (episodes_is_enabled()): ?><script type="text/javascript">window.postMessage("EPISODES:measure:episodes", document.location);window.postMessage("EPISODES:mark:css", document.location);</script><? endif; ?>
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

Written as part of a bachelor thesis at the School for Information Technology
of the Transnational University of Limburg.

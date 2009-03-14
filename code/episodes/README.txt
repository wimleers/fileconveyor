$Id$

Description
-----------


Installation
------------
1) Place this module directory in your "modules" folder (this will usually be
"sites/all/modules/"). Don't install your module in Drupal core's "modules"
folder, since that will cause problems and is bad practice in general. If
"sites/all/modules" doesn't exist yet, just create it.

2) Enable the module.

3) Visit "admin/settings/episodes" to learn about the various settings.


Additional measurements: episodes, css, headerjs, footerjs
----------------------------------------------------------
It's possible to perform additional measurements but it requires that you
alter the page.tpl.php file of your theme.
All you have to do is change this:

    <?php print $head ?>
    <?php print $styles ?>
    <?php print $scripts ?>
to:
    <script type="text/javascript">window.postMessage("EPISODES:mark:episodes", document.location);</script>
    <?php print $head ?>
    <script type="text/javascript">window.postMessage("EPISODES:measure:episodes", document.location);window.postMessage("EPISODES:mark:css", document.location);</script>
    <?php print $styles ?>
    <script type="text/javascript">window.postMessage("EPISODES:measure:css", document.location);window.postMessage("EPISODES:mark:headerjs", document.location);</script>
    <?php print $scripts ?>
    <script type="text/javascript">window.postMessage("EPISODES:measure:headerjs", document.location);</script>

And:
    <?php print $closure ?>
to:
    <?php if (strlen(drupal_get_js('footer'))): ?><script type="text/javascript">window.postMessage("EPISODES:mark:footerjs", document.location);</script><? endif; ?>
    <?php print $closure ?>
    <?php if (strlen(drupal_get_js('footer'))): ?><script type="text/javascript">window.postMessage("EPISODES:measure:footerjs", document.location);</script><? endif; ?>

Really, that's all there is to it!


Author
------
Wim Leers ~ http://wimleers.com/

Written as part of a bachelor thesis at the School for Information Technology
of the Transnational University of Limburg.

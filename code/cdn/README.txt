$Id$

Description
-----------
The aim of this module to provide easy Content Delivery Network integration
for Drupal sites. Obviously it has to patch Drupal core to rewrite the URLs.
URLs must be rewritten to be able to actually serve the files from a CDN.

It provides two modes: basic and advanced.

In basic mode, only "Origin Pull" CDNs are supported. These are CDNs that only
require you to replace the domain name (and possibly base path) with another
domain name. The CDN will then automatically fetch (pull) the files from your
server (the origin).

In advanced mode, you must install and configure the daemon I wrote as part of
my bachelor thesis. This allows for much more advanced setups: files can be
processed before they are synced and your CDN doesn't *have* to support
Origin Pull, any push method is fine. Push always uses transfer protocols,
either well-established ones (e.g. FTP) or custom ones (e.g. Amazon S3). It is
thanks to this abstraction layer that it can be used for *any* CDN, thereby
avoiding vendor lock-in.

This module was written as part of the bachelor thesis [1] of Wim Leers at
Hasselt University [3].

[1] http://wimleers.com/tags/bachelor-thesis
[2] http://uhasselt.be/


Supported CDNs
--------------
- Basic mode: any Origin Pull CDN.
- Advanced mode: any Origin Pull CDN and any push CDN that supports FTP.
  Support for other transfer protocols is welcomed and encouraged: your
  patches are welcome! Amazon S3 and Amazon CloudFront are also supported.


Installation
------------
1) Apply the Drupal core patch (patches/drupal.patch). Instructions can be
   found at http://drupal.org/patch/apply.

2) Place this module directory in your "modules" folder (this will usually be
   "sites/all/modules/"). Don't install your module in Drupal core's "modules"
   folder, since that will cause problems and is bad practice in general. If
   "sites/all/modules" doesn't exist yet, just create it.

3) Enable the module.

4) Visit "admin/settings/cdn" to learn about the various settings.

5) If you want to use advanced mode, install and configure the daemon first.
   You can install it by performing an svn checkout from
     svn://wimleers.com/school/bachelor-thesis/code/daemon
   Then follow the instructions in the included INSTALL.txt and README.txt.
   Use the config.xml file that is included in this module and modify it to
   comply with your setup and to suit your needs.

6) Go to admin/reports/status. The CDN integration module will report its
   status here. If you've enabled advanced mode and have set up the daemon,
   you will see some basic stats here as well, and you can check here to see
   if the daemon is currently running.


When using multiple servers: picking a specific one based on some criteria
--------------------------------------------------------------------------
For this purpose, you can implement the cdn_advanced_pick_server() function:
  /**
   * Implementation of cdn_advanced_pick_server().
   */
  function cdn_advanced_pick_server($servers_for_file) {
    // The data that you get - one nested array per server from which the file
    // can be served:
    //   $servers_for_file[0] = array('url' => 'http://cdn1.com/image.jpg', 'server' => 'cdn1.com')
    //   $servers_for_file[1] = array('url' => 'http://cdn2.net/image.jpg', 'server' => 'cdn2.net')

    $which = your_logic_to_pick_a_server();

    // Return one of the nested arrays.
    return $servers_for_file[$which];
  }

So to get the default behavior (pick the first server found), one would write:
  /**
   * Implementation of cdn_advanced_pick_server().
   */
  function cdn_advanced_pick_server($servers_for_file) {
    return $servers_for_file[0];
  }


Supporting the CDN integration module in your modules
-----------------------------------------------------
It's very easy to support the CDN integration module in your module. Simply
create a variable function, e.g.:
  $file_create_url = (module_exists('cdn')) ? 'file_create_url' : 'url';

Then create all file URLs using this variable function. E.g.
  $file_url = $file_create_url(drupal_get_path('module', 'episodes') .'/lib/episodes.js');


Author
------
Wim Leers ~ http://wimleers.com/

This module was written as part of the bachelor thesis of Wim Leers at
Hasselt University.

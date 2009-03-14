// $Id: hierarchical_select.js,v 1.88 2009/03/07 16:57:08 wimleers Exp $

var foo = 'bar';

Drupal.behaviors.HierarchicalSelect =     function (context) {
  $('.hierarchical-select-wrapper:not(.hierarchical-select-wrapper-processed)', context)
  .addClass('hierarchical-select-wrapper-processed').each(function() {
    var hsid = $(this).attr('id').replace(/^hierarchical-select-(\d+)-wrapper$/, "$1");
    Drupal.HierarchicalSelect.initialize(hsid);
  });
};


/**
 * Attaches the autocomplete behavior to all required fields
 */
Drupal.behaviors.autocomplete = function (context) {
}

Drupal.behaviors.sdfsfHierarchicalSelect = 				function (context) {
  $('.hierarchical-select-wrapper:not(.hierarchical-select-wrapper-processed)', context)
  .addClass('hierarchical-select-wrapper-processed').each(function() {
    var hsid = $(this).attr('id').replace(/^hierarchical-select-(\d+)-wrapper$/, "$1");
    Drupal.HierarchicalSelect.initialize(hsid);
  });
};

/**
 * Scroll a given fieldset into view as much as possible.
 */
Drupal.collapseScrollIntoView = function (node) {
  var h = self.innerHeight || document.documentElement.clientHeight || $('body')[0].clientHeight || 0;
  var offset = self.pageYOffset || document.documentElement.scrollTop || $('body')[0].scrollTop || 0;
  var posY = $(node).offset().top;
  var fudge = 55;
  if (posY + node.offsetHeight + fudge > h + offset) {
    if (node.offsetHeight > h) {
      window.scrollTo(0, posY);
    } else {
      window.scrollTo(0, posY + node.offsetHeight - h + fudge);
    }
  }
};

Drupal.behaviors.collapse = function (context) {
  $('fieldset.collapsible > legend:not(.collapse-processed)', context).each(function() {
    var fieldset = $(this.parentNode);
    // Expand if there are errors inside
    if ($('input.error, textarea.error, select.error', fieldset).size() > 0) {
      fieldset.removeClass('collapsed');
    }

    // Turn the legend into a clickable link and wrap the contents of the fieldset
    // in a div for easier animation
    var text = this.innerHTML;
      $(this).empty().append($('<a href="#">'+ text +'</a>').click(function() {
        var fieldset = $(this).parents('fieldset:first')[0];
        // Don't animate multiple times
        if (!fieldset.animating) {
          fieldset.animating = true;
          Drupal.toggleFieldset(fieldset);
        }
        return false;
      }))
      .after($('<div class="fieldset-wrapper"></div>')
      .append(fieldset.children(':not(legend):not(.action)')))
      .addClass('collapse-processed');
  });
};

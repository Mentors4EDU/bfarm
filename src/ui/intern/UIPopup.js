/**
 * Copyright (C) 2010 Sergey I. Sharybin
 */

function _IUIPopup ()
{
  /**
   * Show popup object at specified point
   *
   * Point is an object with structure {x, y}
   */
  this.popupAt = function (point)
    {
    };

  /**
   * Hide popup
   */
  this.hidePopup = function ()
    {
    };

  /**
   * Set z-index position
   */
  this.setPupZIndex = function (zIndex)
    {
    };
}

function IUIPopup ()
{
}

IUIPopup.prototype = new _IUIPopup;
IUIPopup.prototype.constructor = IUIPopup;

function _UIPopupManager ()
{
  _IObject.call (this);

  /**
   * Call object's handler
   */
  this.callHandler = function (item, handler)
    {
      if (item && item['opts'] && item['opts'][handler])
        {
          item['opts'][handler] ();
        }
    };

  /**
   * Call object's handler (outside current thread)
   */
  this.callOutHandler = function (item, handler)
    {
      window.setTimeout (function (self, item, handler) { return function () {
            self.callHandler (item, handler);
          }
        } (this, item, handler), 5)
    };

  /**
   * Show new popup object
   */
  this.popup = function (object, point, opts)
    {
      if (point['pos'])
        {
          point['x'] = point['pos']['x'];
          point['y'] = point['pos']['y'];
        }

      callOut (function (args) {
          var context = args['object'].getUIContext ();
          object.popupAt (args['point']);

          // XXX: need registration of zIndex in viewport and object's
          //      viewport should be used instead of main
          var zIndex = uiMainViewport.getZIndex ().getLastIndex () + 1;
          object.setPupZIndex (zIndex);

          var item = {'object' : args['object'],
                      'opts'   : args['opts'],
                      'context': context};
          args['this'].stack.push (item);

          uiManager.registerContext (context);

          args['this'].callOutHandler (item, 'onShow');
        }, mkargs (['object', 'point', 'opts'], arguments, {'this': this}));
    }

  /**
   * Handler of click event
   */
  this.clickHandler = function (userData)
    {
      var context = userData['context'];
      var top = this.topItem ();

      if (!top || top['context'] == context)
      {
        return;
      }

      this.hideFromContext (context);

      userData.cancel (true);
    };

  /**
   * Handler of keypress event
   */
  this.keypressHandler = function (userData)
    {
      var event = userData['domEvent'];

      if (event.keyCode == 27 && this.stack.length)
        {
          this.hideTopLevel ();
          userData.cancel (true);
        }
    };

  /**
   * Hide item from stack
   */
  this.hideStackItem = function (item)
    {
      var obj = item['object'];

      obj.hidePopup ();

      this.callHandler (item, 'onHide');

      var index = indexOf (this.stack, item);
      this.stack.splice (index, 1);
    };

  /**
   * Hide top-level popup object
   */
  this.hideTopLevel = function ()
    {
      if (this.stack.length)
        {
          var item = this.stack[this.stack.length - 1];
          this.hideStackItem (item);
        }
    };

  /**
   * Hide all popups from specified stack item
   */
  this.hideFromStackItem = function (item, hideLayer)
    {
      var delta = 1;
      if (hideLayer)
        delta = 0;

      var index = item ? indexOf (this.stack, item) + delta : 0;

      for (var i = this.stack.length - 1; i >= index; --i)
        {
          this.hideStackItem (this.stack[i]);
        }
    };

  /**
   * Hide all popups
   */
  this.hideAll = function ()
    {
      this.hideFromStackItem (null);
    };

  /**
   * Hide all objects from specified
   */
  this.hide = function (object)
    {
      for (var i = 0, n = this.stack.length; i < n; ++i)
        {
          var item = this.stack[i];

          if (item['object'] == object)
            {
              this.hideFromStackItem (item, true);
              break;
            }
        }
    }

  /**
   * Hide all popups from specified context
   */
  this.hideFromContext = function (context)
    {
      var item = this.getPopupByContext (context);
      this.hideFromStackItem (item);
    };

  /**
   * Get popup object descriptor by it's context
   */
  this.getPopupByContext = function (context)
    {
      for (var i = 0, n = this.stack.length; i < n; ++i)
        {
          var item = this.stack[i];

          if (item['context'] == context)
            {
              return item;
            }
        }

      return null;
    };

  /**
   * Get stack's top item
   */
  this.topItem = function ()
    {
      return this.stack.length ? this.stack[this.stack.length - 1] : null;
    };
}

function UIPopupManager ()
{
  IObject.call (this);

  /* Stack of popupped objects */
  this.stack = [];

  /* Handle click callback for hiding popup objects which are */
  /* "outside" of clicked place */
  uiManager.addHandler ('click', function (self) {
      return function (userData) {
        self.clickHandler (userData);
      };
    } (this));

  uiManager.addHandler (['mousedownCancel', 'clickCancel'], function (self) {
    return function (userData) {
      self.hideFromContext (userData['context']);
    };
  } (this));

  /* Use keyup instead of keypress to get ompatibility with more browsers */
  uiManager.addHandler ('keyup', function (self) {
      return function (userData) {
        self.keypressHandler (userData);
      };
    } (this));
}

UIPopupManager.prototype = new _UIPopupManager;
UIPopupManager.prototype.constructor = UIPopupManager;

var uiPopupManager = new UIPopupManager;

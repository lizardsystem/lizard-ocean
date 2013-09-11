// jslint configuration; btw: don't put a space before 'jslint' below.
/*jslint browser: true */
/*global $, OpenLayers, window, map */

// Console-polyfill. MIT license.
// https://github.com/paulmillr/console-polyfill
// Make it safe to do console.log() always.
(function (con) {
  'use strict';
  var prop, method;
  var empty = {};
  var dummy = function() {};
  var properties = 'memory'.split(',');
  var methods = ('assert,count,debug,dir,dirxml,error,exception,group,' +
     'groupCollapsed,groupEnd,info,log,markTimeline,profile,profileEnd,' +
     'time,timeEnd,trace,warn').split(',');
  while (prop = properties.pop()) con[prop] = con[prop] || empty;
  while (method = methods.pop()) con[method] = con[method] || dummy;
})(window.console = window.console || {});

(function () {
    var CssHideableWMSLayer = OpenLayers.Class(OpenLayers.Layer.WMS, {
        cssVisibility: true,
        isAnimated: true,
        frameIndex: null,
        frameLabel: '',

        initialize: function (name, url, params, options) {
            OpenLayers.Layer.WMS.prototype.initialize.apply(
                this, [name, url, params, options]);
            if (options.cssVisibility === true || options.cssVisibility === false) {
                this.cssVisibility = options.cssVisibility;
            }
            this.frameIndex = options.frameIndex;
            if (options.frameLabel) {
                this.frameLabel = options.frameLabel;
            }
            this.events.on({
                'added': this.updateCssVisibility,
                'moveend': this.updateCssVisibility,
                scope: this});
        },

        destroy: function () {
            this.events.un({
                'added': this.updateCssVisibility,
                'moveend': this.updateCssVisibility,
                scope: this});
            OpenLayers.Layer.WMS.prototype.destroy.apply(this);
        },

        setCssVisibility: function (visible) {
            this.cssVisibility = visible;
            this.updateCssVisibility();
        },

        updateCssVisibility: function () {
            if (this.div) {
                if (this.cssVisibility) {
                    $(this.div).show();
                }
                else {
                    $(this.div).hide();
                }
            }
        }
    });

    var CssHideableImageLayer = OpenLayers.Class(OpenLayers.Layer.Image, {
        cssVisibility: true,
        isAnimated: true,
        frameIndex: null,
        frameLabel: '',

        initialize: function (name, url, extent, size, options) {
            OpenLayers.Layer.Image.prototype.initialize.apply(
                this, [name, url, extent, size, options]);
            if (options.cssVisibility === true || options.cssVisibility === false) {
                this.cssVisibility = options.cssVisibility;
            }
            this.frameIndex = options.frameIndex;
            if (options.frameLabel) {
                this.frameLabel = options.frameLabel;
            }
            this.events.on({
                'added': this.updateCssVisibility,
                'moveend': this.updateCssVisibility,
                scope: this});
        },

        destroy: function () {
            this.events.un({
                'added': this.updateCssVisibility,
                'moveend': this.updateCssVisibility,
                scope: this});
            OpenLayers.Layer.Image.prototype.destroy.apply(this);
        },

        setCssVisibility: function (visible) {
            this.cssVisibility = visible;
            this.updateCssVisibility();
        },

        updateCssVisibility: function () {
            if (this.div) {
                if (this.cssVisibility) {
                    $(this.div).show();
                }
                else {
                    $(this.div).hide();
                }
            }
        }
    });

    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    var frames = {};
    var frameCount = 0;

    var frameDurationMs = 1000;
    var animationInterval = null;
    var currentFrameIndex = -1;

    var loadingLayersCount = 0;
    var loadingProgressInterval = null;

    var controlsInitialized = false;
    var $startStopButton;
    var $currentFrameIndexLabel;
    var $frameSlider;
    var $progressBar;
    var $currentFilenameLabel;
    var currentFilenameLabelHideTimeout = null;

    function updateFrames (newFrames) {
        var wasRunning = stopIfRunning();

        // Iterate through all layers, and remove the ones that aren't
        // present in the workspace anymore.

        // Find out what is missing, and what is new. We don't deal with updates.
        var toAdd = [];
        var toRemove = [];
        $.each(frames, function (workspaceItemId, workspaceItemFrames) {
            if (!(workspaceItemId in newFrames)) {
                toRemove.push(workspaceItemId);
            }
        });
        $.each(newFrames, function (workspaceItemId, workspaceItemFrames) {
            if (!(workspaceItemId in frames)) {
                toAdd.push(workspaceItemId);
            }
        });

        // Remove all related layers from the map.
        $.each(toRemove, function () {
            var workspaceItemId = this;
            var workspaceItemFrames = frames[workspaceItemId];
            $.each(workspaceItemFrames, function () {
                try {
                    map.removeLayer(this);
                }
                catch (e) {
                    console.error('map.removeLayer error');
                }
            });
            delete frames[workspaceItemId];
        });

        // Add any new layers to the map.
        $.each(toAdd, function () {
            var workspaceItemId = this;
            var workspaceItemFrames = newFrames[workspaceItemId];
            $.each(workspaceItemFrames, function () {
                try {
                    map.addLayer(this);
                }
                catch (e) {
                    console.error('map.addLayer error');
                }
            });
            frames[workspaceItemId] = workspaceItemFrames;
        });

        updateFrameCount();

        // Find out a frame to show.
        if (hasFrames()) {
            if (currentFrameIndex === -1) {
                // First time, so show the first frame.
                setFrame(0, true);
            }
            else if (frameCount > currentFrameIndex) {
                // If we still have this frame, reactivate it.
                setFrame(currentFrameIndex, true);
            }
            else {
                // frameCount decreased, go to the last available frame.
                setFrame(frameCount - 1, true);
            }
        }
        else {
            // No frames, reset the current frame index to its default.
            setFrame(-1, true);
        }

        // Continue, if we were animating.
        if (hasFrames() && wasRunning) {
            start();
        }
    }

    function updateFrameCount () {
        // calculate highest amount of frames
        frameCount = 0;
        $.each(frames, function (workspaceItemId, workspaceItemFrames) {
            if (workspaceItemFrames.length > frameCount) {
                frameCount = workspaceItemFrames.length;
            }
        });

        onFrameCountChanged();
    }

    function getFramesByIndex (frameIndex) {
        var result = [];
        $.each(frames, function (workspaceItemId, workspaceItemFrames) {
            if (frameIndex in workspaceItemFrames) {
                result.push(workspaceItemFrames[frameIndex]);
            }
        });
        return result;
    }

    function getAllFramesFlat () {
        var result = [];
        $.each(frames, function (workspaceItemId, workspaceItemFrames) {
            $.each(workspaceItemFrames, function () {
                result.push(this);
            });
        });
        return result;
    }

    function setFrame (newFrameIndex, force) {
        console.log('setFrame ', newFrameIndex);

        if (currentFrameIndex !== newFrameIndex || force === true) {
            // swap out visibility
            if (currentFrameIndex !== -1) {
                var currentFrames = getFramesByIndex(currentFrameIndex);
                $.each(currentFrames, function () {
                    this.setCssVisibility(false);
                });
            }
            if (newFrameIndex !== -1) {
                var newFrames = getFramesByIndex(newFrameIndex);
                var frameLabels = [];
                $.each(newFrames, function () {
                    this.setCssVisibility(true);
                    frameLabels.push(this.frameLabel);
                });
                if (frameLabels) {
                    setFilenameLabel(frameLabels);
                }
            }
            else {
                setFilenameLabel([]);
            }

            // update with next layer index
            currentFrameIndex = newFrameIndex;

            onFrameChanged();
        }
    }

    function showNextFrame () {
        if (hasFrames()) {
            var currentFrames = getFramesByIndex(currentFrameIndex);
            var oneFrameIsLoaded = false;
            $.each(currentFrames, function () {
                if (!this.loading) {
                    oneFrameIsLoaded = true;
                }
            });
    
            // don't swap frames when we're still loading
            if (oneFrameIsLoaded) {
                // figure out next frame
                var nextFrameIndex = (currentFrameIndex >= (frameCount - 1)) ? 0 : currentFrameIndex + 1;
                setFrame(nextFrameIndex);
            }
       }
    }

    function createFrame (workspaceItemId, workspaceItemName, workspaceItemWmsParams, workspaceItemOptions, workspaceItemUrl, workspaceItemIndex, filename, frameIndex) {
        var name = workspaceItemName + '_' + workspaceItemId + '_' + frameIndex;

        var wmsUrl = workspaceItemUrl;
        var wmsParams = $.extend({}, workspaceItemWmsParams);
        wmsParams['tilesorigin'] = [map.maxExtent.left, map.maxExtent.bottom];
        wmsParams['filename'] = filename;
        var frameLabel = filename;
        frameLabel = frameLabel.replace(/\.\w+$/g, '');
        frameLabel = frameLabel.replace(/_/g, ' ');
        frameLabel = frameLabel.replace(/\./g, ' ');

        var options = $.extend({}, workspaceItemOptions, {
            opacity: 0.9,
            attribution: 'Powered by Lizard',
            isBaseLayer: false,
            visibility: true, // keep this, so all layers are preloaded in the browser
            cssVisibility: false, // hide layer again with this custom option
            displayInLayerSwitcher: false,
            eventListeners: {
                'loadstart': function () {
                    loadingLayersCount++;
                    onLayerLoadingChange();
                },
                'loadend': function () {
                    loadingLayersCount--;
                    onLayerLoadingChange();
                }
            },
            projection: 'EPSG:900913',
            frameIndex: frameIndex,
            frameLabel: frameLabel
        });

        var olLayer = new CssHideableWMSLayer(
            name,
            wmsUrl,
            wmsParams,
            options
        );

        return olLayer;
    }

    function onFrameCountChanged () {
        if (hasFrames()) {
            $startStopButton.removeAttr('disabled');
            $frameSlider.slider('enable');
            $frameSlider.slider('option', 'max', frameCount - 1);
        }
        else {
            setLoadingProgress(0);
            $startStopButton.attr('disabled', 'disabled');
            $frameSlider.slider('option', 'max', 0);
            $frameSlider.slider('disable');
        }
    }

    function onFrameChanged () {
        if (currentFrameIndex !== -1) {
            $frameSlider.slider('value', currentFrameIndex);
        }
        else {
            $frameSlider.slider('value', 0);
        }
    }

    function hasFrames () {
        return frameCount > 0;
    }

    function initFrameSlider () {
        $frameSlider = $('#frame-slider');
        $currentFrameIndexLabel = $("#current-frame-index-label");
        $frameSlider.slider({
            min: 0,
            max: 0,
            value: 0,
            change: function (event, ui) {
                $currentFrameIndexLabel.text(ui.value + 1);
            },
            slide: function (event, ui) {
                stopIfRunning();
                setFrame(ui.value);
                // Hack: force triggering a change event while sliding.
                var sliderData = $frameSlider.data('slider');
                sliderData._trigger('change', event, ui);
            }
        });
    }

    function initFilenameLabel () {
        $currentFilenameLabel = $('<div id="current-filename-label">');
        $currentFilenameLabel.css({
            'position': 'absolute',
            'right': '10px',
            'top': '100px',
            'border-radius': '4px',
            'background-color': '#fff',
            'padding': '3px',
            'z-index': '10000'
        });
        $currentFilenameLabel.appendTo('body');
    }

    function setFilenameLabel (lineArray) {
        if (currentFilenameLabelHideTimeout !== null) {
            clearTimeout(currentFilenameLabelHideTimeout);
            currentFilenameLabelHideTimeout = null;
        }

        var html = '';
        $.each(lineArray, function () {
            html += this + '<br/>';
        });

        if (html) {
            $currentFilenameLabel.html(html);
            $currentFilenameLabel.show();

            currentFilenameLabelHideTimeout = setTimeout(function () {
                $currentFilenameLabel.hide();
                currentFilenameLabelHideTimeout = null;
            }, 5000);
        }
        else {
            $currentFilenameLabel.hide();
        }
    }

    function start () {
        if (!isRunning() && hasFrames()) {
            $startStopButton.find('i').removeClass('icon-play').addClass('icon-pause');
            $startStopButton.addClass('active');
            animationInterval = setInterval(showNextFrame, frameDurationMs);
        }
    }

    function stop () {
        if (isRunning()) {
            $startStopButton.find('i').removeClass('icon-pause').addClass('icon-play');
            $startStopButton.removeClass('active');
            clearInterval(animationInterval);
            animationInterval = null;
        }
    }

    /**
     * Returns whether the animation was running in the first place.
     */
    function stopIfRunning () {
        if (isRunning()) {
            stop();
            return true;
        }
        return false;
    }

    function isRunning () {
        return animationInterval !== null;
    }

    function toggle () {
        if (isRunning()) {
            stop();
        }
        else {
            start();
        }
    }

    function initStartStopButton () {
        $startStopButton = $('#start-stop-button');
        $startStopButton.click(function (e) {
            if (e) {
                e.preventDefault();
            }
            toggle();
        });
    }

    function initProgressBar () {
        $progressBar = $('#progress-bar');
    }

    function onLayerLoadingChange () {
        if (loadingLayersCount > 0) {
            if (loadingProgressInterval === null) {
                setLoadingProgress(0);
                loadingProgressInterval = setInterval(updateLoadingProgress, 300);
            }
        }
        else {
            if (loadingProgressInterval !== null) {
                clearInterval(loadingProgressInterval);
                loadingProgressInterval = null;
                setLoadingProgress(1);
            }
        }
    }

    function updateLoadingProgress () {
        var numLoadingTiles = 0;
        var numTiles = 0;
        var ratio;
        // sum numLoadingTiles and total amount of tiles per layer
        var frames = getAllFramesFlat();
        $.each(frames, function (idx, frame) {
            if (frame.grid) {
                numLoadingTiles += frame.numLoadingTiles;
                for (var i = 0; i < frame.grid.length; i++) {
                    numTiles += frame.grid[i].length;
                }
            }
        });
        if (numTiles > 0) {
            ratio = 1 - numLoadingTiles / numTiles;
            setLoadingProgress(ratio);
        }
        else {
            // no tiled/gridded layers
            ratio = 1 - loadingLayersCount / frames.length;
            setLoadingProgress(ratio);
        }
    }

    function setLoadingProgress (ratio) {
        // clamp ratio
        if (ratio < 0) ratio = 0;
        if (ratio >= 1) ratio = 1;

        var pct = ratio * 100 + '%';
        $progressBar.find('.bar').css({width: pct});
    }

    function refreshAnimatedLayers () {
        initControls();

        var newFrames = {};
        $('#lizard-map-wms .lizard-map-wms-item[data-workspace-wms-needs-custom-handler="true"]').each(function () {
            var $el = $(this);
            var workspaceItemId = $el.data('workspace-wms-id');
            var workspaceItemName = $el.data('workspace-wms-name');
            var workspaceItemWmsParams = $el.data('workspace-wms-params');
            var workspaceItemOptions = $el.data('workspace-wms-options');
            var workspaceItemUrl = $el.data('workspace-wms-url');
            var workspaceItemIndex = $el.data('workspace-wms-index');
            var handlerData = $el.data('workspace-wms-custom-handler-data');

            var workspaceItemFrames = [];
            $.each(handlerData.filenames, function (frameIndex) {
                var filename = this;
                var frame = createFrame(workspaceItemId, workspaceItemName, workspaceItemWmsParams, workspaceItemOptions, workspaceItemUrl, workspaceItemIndex, filename, frameIndex);
                workspaceItemFrames.push(frame);
            });
            newFrames[workspaceItemId] = workspaceItemFrames;
        });

        updateFrames(newFrames);
    }

    function initControls () {
        if (!controlsInitialized) {
            initStartStopButton();
            initFrameSlider();
            initFilenameLabel();
            initProgressBar();
            map.addControl(new OpenLayers.Control.Attribution());
            controlsInitialized = true;
       }
    }

    window.refreshAnimatedLayers = refreshAnimatedLayers;

    // force i18n to english
    moment.lang('en');
})();

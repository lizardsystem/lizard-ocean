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

/* ******************************************************************** */
/* ******************************************************************** */
/* ******************************************************************** */
/* ******************************************************************** */
/* ******************************************************************** */
/* ******************************************************************** */
(function () {
    var RASTER_LAYER_ZINDEX = 700;
    var LOCATIONS_LAYER_ZINDEX = 1000;

    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
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

    function refreshAnimatedLayers (rastersets) {
        var newFrames = {};
        $.each(rastersets, function () {
            var rasterset = this;
            var frames = [];
            $.each(rasterset.children, function (frameIndex) {
                var child = this;
                var frame = createFrame(rasterset.identifier, rasterset.name, child.identifier, child.name, frameIndex);
                frames.push(frame);
            });
            newFrames[rasterset.identifier] = frames;
        });

        updateFrames(newFrames);
    }

    function updateFrames (newFrames) {
        var wasRunning = stopIfRunning();

        // Iterate through all layers, and remove the ones that aren't
        // present in the selected frames anymore.

        // Find out what is missing, and what is new. We don't deal with updates.
        var toAdd = [];
        var toRemove = [];
        $.each(frames, function (frameSetId, frameSetFrames) {
            if (!(frameSetId in newFrames)) {
                toRemove.push(frameSetId);
            }
        });
        $.each(newFrames, function (frameSetId, frameSetFrames) {
            if (!(frameSetId in frames)) {
                toAdd.push(frameSetId);
            }
        });

        // Remove all related layers from the map.
        $.each(toRemove, function () {
            var frameSetId = this;
            var frameSetFrames = frames[frameSetId];
            $.each(frameSetFrames, function () {
                try {
                    map.removeLayer(this);
                }
                catch (e) {
                    console.error('map.removeLayer error');
                }
            });
            delete frames[frameSetId];
        });

        // Add any new layers to the map.
        $.each(toAdd, function () {
            var frameSetId = this;
            var frameSetFrames = newFrames[frameSetId];
            $.each(frameSetFrames, function () {
                try {
                    map.addLayer(this);
                    this.setZIndex(RASTER_LAYER_ZINDEX);
                }
                catch (e) {
                    console.error('map.addLayer error');
                }
            });
            frames[frameSetId] = frameSetFrames;
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
        $.each(frames, function (frameSetId, frameSetFrames) {
            if (frameSetFrames.length > frameCount) {
                frameCount = frameSetFrames.length;
            }
        });

        onFrameCountChanged();
    }

    function getFramesByIndex (frameIndex) {
        var result = [];
        $.each(frames, function (frameSetId, frameSetFrames) {
            if (frameIndex in frameSetFrames) {
                result.push(frameSetFrames[frameIndex]);
            }
        });
        return result;
    }

    function getAllFramesFlat () {
        var result = [];
        $.each(frames, function (frameSetId, frameSetFrames) {
            $.each(frameSetFrames, function () {
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

    function createFrame (rastersetId, rastersetName, frameId, frameName, frameIndex) {
        var name = frameId;

        var wmsUrl = '/ocean/ejwms/';
        var wmsParams = $.extend({}, {
            tilesorigin: [map.maxExtent.left, map.maxExtent.bottom],
            layers: frameId,
            filterbytype: 'rasters'
        });
        var frameLabel = frameName;
        frameLabel = frameLabel.replace(/\.\w+$/g, '');
        frameLabel = frameLabel.replace(/_/g, ' ');
        frameLabel = frameLabel.replace(/\./g, ' ');

        var options = $.extend({}, {
            singleTile: true,
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

    function initAnimationControls () {
        if (!controlsInitialized) {
            initStartStopButton();
            initFrameSlider();
            initFilenameLabel();
            initProgressBar();
            map.addControl(new OpenLayers.Control.Attribution());
            controlsInitialized = true;
       }
    }

    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */
    /* ******************************************************************** */

    function getIdentifiers (nodes) {
        var identifiers = [];
        $.each(nodes, function () {
            var node = this;
            identifiers.push(node.data.identifier);
        });
        return identifiers;
    }

    $(document).ready(function () {
        // Force i18n to English.
        moment.lang('en');

        // Add a single OL layer for the locations.
        var locationsLayer = new OpenLayers.Layer.WMS('locations', '/ocean/ejwms/',
        {
            layers: [],
            format: 'image/png',
            filterbytype: 'locations'
        },
        {
            isBaseLayer: false,
            singleTile: true,
            displayInLayerSwitcher: false
        });
        map.addLayer(locationsLayer);
        locationsLayer.setZIndex(LOCATIONS_LAYER_ZINDEX);

        // Initialize rastersets animation.
        initAnimationControls();
        var refreshRastersetsTimeout = null;
        var refreshRastersetsDeferred = null;
        function getRastersetInfo (identifiers) {
            if (refreshRastersetsDeferred !== null) {
                refreshRastersetsDeferred.abort();
            }
            refreshRastersetsDeferred = $.get('/ocean/ejrastersetinfo/', {identifiers: identifiers.join(',')})
            .done(function (data) {
                var rastersetInfo = data;
                refreshAnimatedLayers(rastersetInfo);
            })
            .fail(function (data) {
                console.log('getRastersetInfo fail');
            })
            .always(function () {
                refreshRastersetsDeferred = null;
            });
        }
        function refreshRastersets (identifiers) {
            if (refreshRastersetsTimeout !== null) {
                window.clearTimeout(refreshRastersetsTimeout);
                refreshRastersetsTimeout = null;
            }
            refreshRastersetsTimeout = window.setTimeout(function () {
                refreshRastersetsTimeout = null;
                getRastersetInfo(identifiers);
            }, 200);
        }

        // Initialize the tree.
        $("#ocean-tree").fancytree({
            source: treeData,
            checkbox: true,
            selectMode: 3,
            debugLevel: 0,
            click: function(e, data) {
                // Toggle node when clicked on the title.
                if (e && e.originalEvent && e.originalEvent.target) {
                    var $target = $(e.originalEvent.target);
                    if ($target.hasClass('fancytree-title')) {
                        data.node.toggleSelected();
                    }
                }
            },
            select: function(event, data) {
                var nodes = data.tree.getSelectedNodes(true);

                var identifiers = getIdentifiers(nodes);
                console.log('identifiers ', identifiers);
                locationsLayer.mergeNewParams({
                    layers: identifiers
                });
                // Need to do this each time after a mergeNewParams.
                locationsLayer.setZIndex(LOCATIONS_LAYER_ZINDEX);
                locationsLayer.redraw(true);

                refreshRastersets(identifiers);
            }
        });
    });
})();

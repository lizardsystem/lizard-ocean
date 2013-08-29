// jslint configuration; btw: don't put a space before 'jslint' below.
/*jslint browser: true */
/*global $, OpenLayers, window, map */

(function () {
    var CssHideableWMSLayer = OpenLayers.Class(OpenLayers.Layer.WMS, {
        cssVisibility: true,
    	isAnimated: true,
        workspaceItemId: null,
        frameIndex: null,

        initialize: function (name, url, params, options) {
            OpenLayers.Layer.WMS.prototype.initialize.apply(
                this, [name, url, params, options]);
            if (options.cssVisibility === true || options.cssVisibility === false) {
                this.cssVisibility = options.cssVisibility;
            }
            this.workspaceItemId = options.workspaceItemId;
            this.frameIndex = options.frameIndex;
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
        workspaceItemId: null,
        frameIndex: null,

        initialize: function (name, url, extent, size, options) {
            OpenLayers.Layer.Image.prototype.initialize.apply(
                this, [name, url, extent, size, options]);
            if (options.cssVisibility === true || options.cssVisibility === false) {
                this.cssVisibility = options.cssVisibility;
            }
            this.workspaceItemId = options.workspaceItemId;
            this.frameIndex = options.frameIndex;
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
	var workspaceItemIdToFrames = {};
	var frameCount = 0;

    var frameDurationMs = 1000;
    var animationInterval = null;
    var currentFrameIndex = -1;
    var lastFrameIndex = -1;

    var loadingLayersCount = 0;
    var loadingProgressInterval = null;

	var controlsInitialized = false;
    var $startStopButton;
    var $currentFrameIndexLabel;
    var $frameSlider;
    var $progressBar;

    function update_animated_layers (newWorkspaceItemIdToFrames) {
		var wasRunning = stop_if_running();

    	// Iterate through all layers, and remove the ones created by us that aren't
    	// present in the workspace anymore.
    	var toAdd = [];
    	var toRemove = [];
    	$.each(workspaceItemIdToFrames, function (workspaceItemId, frames) {
    		if (!(workspaceItemId in newWorkspaceItemIdToFrames)) {
		   		toRemove.push(workspaceItemId);
    		}
    	});
    	$.each(newWorkspaceItemIdToFrames, function (workspaceItemId, frames) {
    		if (!(workspaceItemId in workspaceItemIdToFrames)) {
    			toAdd.push(workspaceItemId);
    		}
    	});
    	$.each(toRemove, function () {
    		var workspaceItemId = this;
    		var frames = workspaceItemIdToFrames[workspaceItemId];
	    	$.each(frames, function () {
	    		try {
					map.removeLayer(this);
				}
				catch (e) {
					console.error('map.removeLayer error');
				}
			});
			delete workspaceItemIdToFrames[workspaceItemId];
    	});
    	$.each(toAdd, function () {
    		var workspaceItemId = this;
    		var frames = newWorkspaceItemIdToFrames[workspaceItemId];
	    	$.each(frames, function () {
	    		try {
					map.addLayer(this);
				}
				catch (e) {
					console.error('map.addLayer error');
				}
			});
			workspaceItemIdToFrames[workspaceItemId] = frames;
    	});

		// calculate highest amount of frames
		frameCount = 0;
    	$.each(workspaceItemIdToFrames, function (workspaceItemId, frames) {
    		if (frames.length > frameCount) {
    			frameCount = frames.length;
    		}
    	});
		$frameSlider.slider('option', 'max', frameCount - 1);

		// if (newWorkspaceItemIdToFrames.length === 0) {
			// currentFrameIndex = -1;
		// }
		// if (currentFrameIndex > (animatedLayers.length - 1)) {
			// currentFrameIndex = 0;
		// }

    	// if (wasRunning && frameCount > 0) {
    		// start();
    	// }

		// go to first frame
		if (frameCount > 0) {
        	set_layer(0);
        }
    }

	function getFramesByIndex(frameIndex) {
		var result = [];
    	$.each(workspaceItemIdToFrames, function (workspaceItemId, frames) {
    		if (frameIndex in frames) {
    			result.push(frames[frameIndex]);
    		}
    	});
    	return result;
	}

	function getAllFrames() {
		var result = [];
    	$.each(workspaceItemIdToFrames, function (workspaceItemId, frames) {
	    	$.each(frames, function () {
    			result.push(this);
    		});
    	});
    	return result;
	}

    function set_layer (newFrameIndex) {
        if (currentFrameIndex != newFrameIndex) {
            // swap out visibility
            if (currentFrameIndex != -1) {
                var currentFrames = getFramesByIndex(currentFrameIndex);
		    	$.each(currentFrames, function () {
	                this.setCssVisibility(false);
		    	});
            }
            if (newFrameIndex != -1) {
                var newFrames = getFramesByIndex(newFrameIndex);
		    	$.each(newFrames, function () {
	                this.setCssVisibility(true);
		    	});
            }

            // update with next layer index
            currentFrameIndex = newFrameIndex;

            on_layer_changed();
        }
    }

    function showNextFrame () {
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
            set_layer(nextFrameIndex);
        }
    }

	function createFrame (workspaceItemId, workspaceItemName, workspaceItemWmsParams, workspaceItemOptions, workspaceItemUrl, workspaceItemIndex, filename, frameIndex) {
        var name = workspaceItemName + '_' + workspaceItemId + '_' + frameIndex;

        var wmsUrl = workspaceItemUrl;
        var wmsParams = $.extend({}, workspaceItemWmsParams);
        wmsParams['tilesorigin'] = [map.maxExtent.left, map.maxExtent.bottom];
        wmsParams['filename'] = filename;

        var options = $.extend({}, workspaceItemOptions, {
            isBaseLayer: false,
            visibility: true, // keep this, so all layers are preloaded in the browser
            cssVisibility: false, // hide layer again with this custom option
            displayInLayerSwitcher: false,
            eventListeners: {
                'loadstart': function () {
                    loadingLayersCount++;
                    on_layer_loading_change();
                },
                'loadend': function () {
                    loadingLayersCount--;
                    on_layer_loading_change();
                }
            },
            projection: 'EPSG:900913',
            workspaceItemId: workspaceItemId,
            frameIndex: frameIndex
        });

        var olLayer = new CssHideableWMSLayer(
            name,
            wmsUrl,
            wmsParams,
            options
        );

		return olLayer;
	}
/*
	function add_animated_layer_frame2 (workspaceItemId, workspaceItemName, workspaceItemWmsParams, workspaceItemOptions, workspaceItemUrl, workspaceItemIndex, filename, frameIndex) {
		var bbox = new OpenLayers.Bounds(5701591, 2748063, 6122300, 2918059);
        var wmsParams = {
            WIDTH: 512,
            HEIGHT: 512,
            SRS: 'EPSG:900913',
            BBOX: bbox.toBBOX(),
            FILENAME: filename,
            LAYERS: workspaceItemWmsParams.layers
        };
        var wmsUrl = workspaceItemUrl + '?' + $.param(wmsParams);
        var ol_layer = new CssHideableImageLayer(
            workspaceItemName + '_' + workspaceItemId + '_' + frameIndex,
            wmsUrl,
            bbox,
            new OpenLayers.Size(512, 512),
            {
                isBaseLayer: false,
                alwaysInRange: true,
                visibility: true, // keep this, so all layers are preloaded in the browser
                cssVisibility: false, // hide layer again with this custom option
                displayInLayerSwitcher: false,
                eventListeners: {
                    'loadstart': function () {
                        loadingLayersCount++;
                        on_layer_loading_change();
                    },
                    'loadend': function () {
                        loadingLayersCount--;
                        on_layer_loading_change();
                    }
                },
                projection: 'EPSG:900913'
            }
        );
        ol_layer.workspaceItemId = workspaceItemId;
        ol_layer.frameIndex = frameIndex;
        map.addLayer(ol_layer);
	}
*/
/*
    function init_cycle_layers () {
        var init_layer = function (idx, layer) {
            var wms_params = {
                WIDTH: 512,
                HEIGHT: 512,
                SRS: 'EPSG:3857',
                BBOX: layer.bbox.toBBOX(),
                FILENAME: layer.filename
            };
            var wms_url = lizard_neerslagradar.wms_base_url + '?' + $.param(wms_params);
            var ol_layer = new CssHideableImageLayer(
                'L' + idx,
                wms_url,
                layer.bbox,
                new OpenLayers.Size(512, 512),
                {
                    isBaseLayer: false,
                    alwaysInRange: true,
                    visibility: true, // keep this, so all layers are preloaded in the browser
                    cssVisibility: false, // hide layer again with this custom option
                    displayInLayerSwitcher: false,
                    metadata: layer,
                    eventListeners: {
                        'loadstart': function () {
                            loadingLayersCount++;
                            on_layer_loading_change();
                        },
                        'loadend': function () {
                            loadingLayersCount--;
                            on_layer_loading_change();
                        }
                    },
                    projection: 'EPSG:3857'
                }
            );
            map.addLayer(ol_layer);
            layer.ol_layer = ol_layer;
        };

        $.each(layers, init_layer);
    }
*/
    function on_layer_changed () {
        if (currentFrameIndex != -1) {
            $frameSlider.slider('value', currentFrameIndex);
        }
    }

    function init_slider () {
        $frameSlider = $('#frame-slider');
        $currentFrameIndexLabel = $("#current-frame-index-label");
        $frameSlider.slider({
            min: 0,
            max: 0,
            change: function (event, ui) {
                $currentFrameIndexLabel.text(ui.value + 1);
            },
            slide: function (event, ui) {
                stop_if_running();
                set_layer(ui.value);
                // hack: force triggering a change event while sliding
                var slider_data = $frameSlider.data('slider');
                slider_data._trigger('change', event, ui);
            }
        });
    }

    function start () {
        $startStopButton.find('i').removeClass('icon-play').addClass('icon-pause');
        $startStopButton.addClass('active');
        animationInterval = setInterval(showNextFrame, frameDurationMs);
    }

    function stop () {
        $startStopButton.find('i').removeClass('icon-pause').addClass('icon-play');
        $startStopButton.removeClass('active');
        clearInterval(animationInterval);
        animationInterval = null;
    }

	/**
	 * Returns whether the animation was running in the first place.
	 */
    function stop_if_running () {
        if (is_running()) {
            stop();
            return true;
        }
        return false;
    }

    function is_running () {
        return animationInterval !== null;
    }

    function toggle () {
        if (is_running()) {
            stop();
        }
        else {
            start();
        }
    }

    function init_button () {
        $startStopButton = $('#start-stop-button');
        $startStopButton.click(function (e) {
            if (e) {
                e.preventDefault();
            }
            toggle();
        });
    }

    function init_progress () {
        $progressBar = $('#progress-bar');
    }

	/**
	 * Disabled for now.
	 */
    function on_layer_loading_change () {
    	return;
        if (loadingLayersCount > 0) {
            // 'if' control structure split for clarity
            if (loadingProgressInterval === null && is_running()) {
                set_progress(0);
                loadingProgressInterval = setInterval(update_progress, 300);
            }
        }
        else {
            if (loadingProgressInterval !== null) {
                clearInterval(loadingProgressInterval);
                loadingProgressInterval = null;
                set_progress(1);
            }
        }
    }

	/**
	 * Unused for now.
	 */
    function update_progress () {
    	return;
        var num_loading_tiles = 0;
        var num_tiles = 0;
        var ratio;
        // sum numLoadingTiles and total amount of tiles per layer
        var layers = getAllFrames();
        $.each(layers, function (idx, layer) {
            if (layer.ol_layer && layer.grid) {
                num_loading_tiles += layer.numLoadingTiles;
                for (var i=0; i<layer.grid.length; i++) {
                    num_tiles += layer.grid[i].length;
                }
            }
        });
        if (num_tiles > 0) {
            ratio = 1 - num_loading_tiles / num_tiles;
            set_progress(ratio);
        }
        else {
            // no tiled/gridded layers
            ratio = 1 - loadingLayersCount / layers.length;
            set_progress(ratio);
        }
    }

	/**
	 * Unused for now.
	 */
    function set_progress (ratio) {
    	return;
        // clamp ratio
        if (ratio < 0) ratio = 0;
        if (ratio >= 1) ratio = 1;

        var isReady = ratio == 1;
        if (isReady) {
            $startStopButton.removeAttr('disabled');
            $frameSlider.slider('enable');
            if (!$startStopButton.hasClass('active')) {
              start();
            }
        }
        else {
            $startStopButton.attr('disabled', 'disabled');
            $frameSlider.slider('disable');
        }
        var pct = ratio * 100 + '%';
        $progressBar.find('.bar').css({width: pct});
    }

	/**
	 * Unused for now.
	 */
    function wait_until_first_layer_loaded () {
    	return;
        var waitInterval = null;
        var tick = function () {
        	var layers = getAllFrames();
            if (layers[0] && !layers[0].loading) {
                set_layer(0);
                // stop self
                clearInterval(waitInterval);
                waitInterval = null;
            }
        };
        set_progress(0);
        loadingProgressInterval = setInterval(update_progress, 300);
        waitInterval = setInterval(tick, 1000);
    }

    function refresh_animated_layers () {
    	init_animation_controls();

    	var newWorkspaceItemIdToFrames = {};
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
			newWorkspaceItemIdToFrames[workspaceItemId] = workspaceItemFrames;
    	});

    	update_animated_layers(newWorkspaceItemIdToFrames);
    }

    function init_animation_controls () {
    	if (!controlsInitialized) {
	        init_button();
	        init_slider();
	        init_progress();
	        controlsInitialized = true;
       }
    }

    window.refresh_animated_layers = refresh_animated_layers;
})();

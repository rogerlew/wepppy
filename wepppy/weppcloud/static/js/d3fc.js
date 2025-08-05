(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('d3-array'), require('d3-scale'), require('d3-time'), require('d3-random'), require('d3-fetch'), require('d3-path'), require('d3-selection'), require('d3-shape'), require('d3-scale-chromatic'), require('d3-dispatch'), require('d3-brush'), require('d3-zoom')) :
    typeof define === 'function' && define.amd ? define(['exports', 'd3-array', 'd3-scale', 'd3-time', 'd3-random', 'd3-fetch', 'd3-path', 'd3-selection', 'd3-shape', 'd3-scale-chromatic', 'd3-dispatch', 'd3-brush', 'd3-zoom'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.fc = {}, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3, global.d3));
})(this, (function (exports, d3Array, d3Scale, d3Time, d3Random, d3Fetch, d3Path, d3Selection, d3Shape, d3ScaleChromatic, d3Dispatch, d3Brush, d3Zoom) { 'use strict';

    var createReboundMethod = (function (target, source, name) {
      var method = source[name];
      if (typeof method !== 'function') {
        throw new Error("Attempt to rebind ".concat(name, " which isn't a function on the source object"));
      }
      return function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        var value = method.apply(source, args);
        return value === source ? target : value;
      };
    });

    var rebind = (function (target, source) {
      for (var _len = arguments.length, names = new Array(_len > 2 ? _len - 2 : 0), _key = 2; _key < _len; _key++) {
        names[_key - 2] = arguments[_key];
      }
      for (var _i = 0, _names = names; _i < _names.length; _i++) {
        var name = _names[_i];
        target[name] = createReboundMethod(target, source, name);
      }
      return target;
    });

    var createTransform = function createTransform(transforms) {
      return function (name) {
        return transforms.reduce(function (name, fn) {
          return name && fn(name);
        }, name);
      };
    };
    var rebindAll = (function (target, source) {
      for (var _len = arguments.length, transforms = new Array(_len > 2 ? _len - 2 : 0), _key = 2; _key < _len; _key++) {
        transforms[_key - 2] = arguments[_key];
      }
      var transform = createTransform(transforms);
      for (var _i = 0, _Object$keys = Object.keys(source); _i < _Object$keys.length; _i++) {
        var name = _Object$keys[_i];
        var result = transform(name);
        if (result) {
          target[result] = createReboundMethod(target, source, name);
        }
      }
      return target;
    });

    var regexify = (function (strsOrRegexes) {
      return strsOrRegexes.map(function (strOrRegex) {
        return typeof strOrRegex === 'string' ? new RegExp("^".concat(strOrRegex, "$")) : strOrRegex;
      });
    });

    var exclude = (function () {
      for (var _len = arguments.length, exclusions = new Array(_len), _key = 0; _key < _len; _key++) {
        exclusions[_key] = arguments[_key];
      }
      exclusions = regexify(exclusions);
      return function (name) {
        return exclusions.every(function (exclusion) {
          return !exclusion.test(name);
        }) && name;
      };
    });

    var include = (function () {
      for (var _len = arguments.length, inclusions = new Array(_len), _key = 0; _key < _len; _key++) {
        inclusions[_key] = arguments[_key];
      }
      inclusions = regexify(inclusions);
      return function (name) {
        return inclusions.some(function (inclusion) {
          return inclusion.test(name);
        }) && name;
      };
    });

    var includeMap = (function (mappings) {
      return function (name) {
        return mappings[name];
      };
    });

    var capitalizeFirstLetter = function capitalizeFirstLetter(str) {
      return str[0].toUpperCase() + str.slice(1);
    };
    var prefix = (function (prefix) {
      return function (name) {
        return prefix + capitalizeFirstLetter(name);
      };
    });

    function identity$5(d) {
      return d;
    }
    function noop(d) {}
    function functor$6(v) {
      return typeof v === 'function' ? v : function () {
        return v;
      };
    }
    function convertNaN(value) {
      return typeof value === 'number' && isNaN(value) ? undefined : value;
    }

    function _slidingWindow () {
      var period = function period() {
        return 10;
      };
      var accumulator = noop;
      var value = identity$5;
      var defined = function defined(d) {
        return d != null;
      };
      var slidingWindow = function slidingWindow(data) {
        var size = period.apply(this, arguments);
        var windowData = data.slice(0, size).map(value);
        return data.map(function (d, i) {
          if (i >= size) {
            // Treat windowData as FIFO rolling buffer
            windowData.shift();
            windowData.push(value(d, i));
          }
          if (i < size - 1 || windowData.some(function (d) {
            return !defined(d);
          })) {
            return accumulator(undefined, i);
          }
          return accumulator(windowData, i);
        });
      };
      slidingWindow.period = function () {
        if (!arguments.length) {
          return period;
        }
        period = functor$6(arguments.length <= 0 ? undefined : arguments[0]);
        return slidingWindow;
      };
      slidingWindow.accumulator = function () {
        if (!arguments.length) {
          return accumulator;
        }
        accumulator = arguments.length <= 0 ? undefined : arguments[0];
        return slidingWindow;
      };
      slidingWindow.defined = function () {
        if (!arguments.length) {
          return defined;
        }
        defined = arguments.length <= 0 ? undefined : arguments[0];
        return slidingWindow;
      };
      slidingWindow.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        return slidingWindow;
      };
      return slidingWindow;
    }

    function bollingerBands () {
      var multiplier = 2;
      var slidingWindow = _slidingWindow().accumulator(function (values) {
        var stdDev = values && d3Array.deviation(values);
        var average = values && d3Array.mean(values);
        return {
          average: average,
          upper: convertNaN(average + multiplier * stdDev),
          lower: convertNaN(average - multiplier * stdDev)
        };
      });
      var bollingerBands = function bollingerBands(data) {
        return slidingWindow(data);
      };
      bollingerBands.multiplier = function () {
        if (!arguments.length) {
          return multiplier;
        }
        multiplier = arguments.length <= 0 ? undefined : arguments[0];
        return bollingerBands;
      };
      rebind(bollingerBands, slidingWindow, 'period', 'value');
      return bollingerBands;
    }

    function exponentialMovingAverage () {
      var value = identity$5;
      var period = function period() {
        return 9;
      };
      var initialMovingAverageAccumulator = function initialMovingAverageAccumulator(period) {
        var values = [];
        return function (value) {
          var movingAverage;
          if (values.length < period) {
            if (value != null) {
              values.push(value);
            } else {
              values = [];
            }
          }
          if (values.length >= period) {
            movingAverage = d3Array.mean(values);
          }
          return movingAverage;
        };
      };
      var exponentialMovingAverage = function exponentialMovingAverage(data) {
        var size = period.apply(this, arguments);
        var alpha = 2 / (size + 1);
        var initialAccumulator = initialMovingAverageAccumulator(size);
        var ema;
        return data.map(function (d, i) {
          var v = value(d, i);
          if (ema === undefined) {
            ema = initialAccumulator(v);
          } else {
            ema = v * alpha + (1 - alpha) * ema;
          }
          return convertNaN(ema);
        });
      };
      exponentialMovingAverage.period = function () {
        if (!arguments.length) {
          return period;
        }
        period = functor$6(arguments.length <= 0 ? undefined : arguments[0]);
        return exponentialMovingAverage;
      };
      exponentialMovingAverage.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        return exponentialMovingAverage;
      };
      return exponentialMovingAverage;
    }

    function macd () {
      var value = identity$5;
      var fastEMA = exponentialMovingAverage().period(12);
      var slowEMA = exponentialMovingAverage().period(26);
      var signalEMA = exponentialMovingAverage().period(9);
      var macd = function macd(data) {
        fastEMA.value(value);
        slowEMA.value(value);
        var diff = d3Array.zip(fastEMA(data), slowEMA(data)).map(function (d) {
          return d[0] !== undefined && d[1] !== undefined ? d[0] - d[1] : undefined;
        });
        var averageDiff = signalEMA(diff);
        return d3Array.zip(diff, averageDiff).map(function (d) {
          return {
            macd: d[0],
            signal: d[1],
            divergence: d[0] !== undefined && d[1] !== undefined ? d[0] - d[1] : undefined
          };
        });
      };
      macd.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        return macd;
      };
      rebindAll(macd, fastEMA, includeMap({
        'period': 'fastPeriod'
      }));
      rebindAll(macd, slowEMA, includeMap({
        'period': 'slowPeriod'
      }));
      rebindAll(macd, signalEMA, includeMap({
        'period': 'signalPeriod'
      }));
      return macd;
    }

    function _arrayLikeToArray(r, a) {
      (null == a || a > r.length) && (a = r.length);
      for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e];
      return n;
    }
    function _arrayWithHoles(r) {
      if (Array.isArray(r)) return r;
    }
    function _arrayWithoutHoles(r) {
      if (Array.isArray(r)) return _arrayLikeToArray(r);
    }
    function _assertThisInitialized(e) {
      if (void 0 === e) throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
      return e;
    }
    function _classCallCheck(a, n) {
      if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function");
    }
    function _construct(t, e, r) {
      if (_isNativeReflectConstruct()) return Reflect.construct.apply(null, arguments);
      var o = [null];
      o.push.apply(o, e);
      var p = new (t.bind.apply(t, o))();
      return r && _setPrototypeOf(p, r.prototype), p;
    }
    function _defineProperties(e, r) {
      for (var t = 0; t < r.length; t++) {
        var o = r[t];
        o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o);
      }
    }
    function _createClass(e, r, t) {
      return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", {
        writable: !1
      }), e;
    }
    function _createForOfIteratorHelper(r, e) {
      var t = "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"];
      if (!t) {
        if (Array.isArray(r) || (t = _unsupportedIterableToArray(r)) || e && r && "number" == typeof r.length) {
          t && (r = t);
          var n = 0,
            F = function () {};
          return {
            s: F,
            n: function () {
              return n >= r.length ? {
                done: !0
              } : {
                done: !1,
                value: r[n++]
              };
            },
            e: function (r) {
              throw r;
            },
            f: F
          };
        }
        throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
      }
      var o,
        a = !0,
        u = !1;
      return {
        s: function () {
          t = t.call(r);
        },
        n: function () {
          var r = t.next();
          return a = r.done, r;
        },
        e: function (r) {
          u = !0, o = r;
        },
        f: function () {
          try {
            a || null == t.return || t.return();
          } finally {
            if (u) throw o;
          }
        }
      };
    }
    function _createSuper(t) {
      var r = _isNativeReflectConstruct();
      return function () {
        var e,
          o = _getPrototypeOf(t);
        if (r) {
          var s = _getPrototypeOf(this).constructor;
          e = Reflect.construct(o, arguments, s);
        } else e = o.apply(this, arguments);
        return _possibleConstructorReturn(this, e);
      };
    }
    function _getPrototypeOf(t) {
      return _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf.bind() : function (t) {
        return t.__proto__ || Object.getPrototypeOf(t);
      }, _getPrototypeOf(t);
    }
    function _inherits(t, e) {
      if ("function" != typeof e && null !== e) throw new TypeError("Super expression must either be null or a function");
      t.prototype = Object.create(e && e.prototype, {
        constructor: {
          value: t,
          writable: !0,
          configurable: !0
        }
      }), Object.defineProperty(t, "prototype", {
        writable: !1
      }), e && _setPrototypeOf(t, e);
    }
    function _isNativeFunction(t) {
      try {
        return -1 !== Function.toString.call(t).indexOf("[native code]");
      } catch (n) {
        return "function" == typeof t;
      }
    }
    function _isNativeReflectConstruct() {
      try {
        var t = !Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {}));
      } catch (t) {}
      return (_isNativeReflectConstruct = function () {
        return !!t;
      })();
    }
    function _iterableToArray(r) {
      if ("undefined" != typeof Symbol && null != r[Symbol.iterator] || null != r["@@iterator"]) return Array.from(r);
    }
    function _iterableToArrayLimit(r, l) {
      var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"];
      if (null != t) {
        var e,
          n,
          i,
          u,
          a = [],
          f = !0,
          o = !1;
        try {
          if (i = (t = t.call(r)).next, 0 === l) {
            if (Object(t) !== t) return;
            f = !1;
          } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0);
        } catch (r) {
          o = !0, n = r;
        } finally {
          try {
            if (!f && null != t.return && (u = t.return(), Object(u) !== u)) return;
          } finally {
            if (o) throw n;
          }
        }
        return a;
      }
    }
    function _nonIterableRest() {
      throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
    }
    function _nonIterableSpread() {
      throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
    }
    function _possibleConstructorReturn(t, e) {
      if (e && ("object" == typeof e || "function" == typeof e)) return e;
      if (void 0 !== e) throw new TypeError("Derived constructors may only return object or undefined");
      return _assertThisInitialized(t);
    }
    function _setPrototypeOf(t, e) {
      return _setPrototypeOf = Object.setPrototypeOf ? Object.setPrototypeOf.bind() : function (t, e) {
        return t.__proto__ = e, t;
      }, _setPrototypeOf(t, e);
    }
    function _slicedToArray(r, e) {
      return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest();
    }
    function _toArray(r) {
      return _arrayWithHoles(r) || _iterableToArray(r) || _unsupportedIterableToArray(r) || _nonIterableRest();
    }
    function _toConsumableArray(r) {
      return _arrayWithoutHoles(r) || _iterableToArray(r) || _unsupportedIterableToArray(r) || _nonIterableSpread();
    }
    function _toPrimitive(t, r) {
      if ("object" != typeof t || !t) return t;
      var e = t[Symbol.toPrimitive];
      if (void 0 !== e) {
        var i = e.call(t, r || "default");
        if ("object" != typeof i) return i;
        throw new TypeError("@@toPrimitive must return a primitive value.");
      }
      return ("string" === r ? String : Number)(t);
    }
    function _toPropertyKey(t) {
      var i = _toPrimitive(t, "string");
      return "symbol" == typeof i ? i : i + "";
    }
    function _typeof(o) {
      "@babel/helpers - typeof";

      return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) {
        return typeof o;
      } : function (o) {
        return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o;
      }, _typeof(o);
    }
    function _unsupportedIterableToArray(r, a) {
      if (r) {
        if ("string" == typeof r) return _arrayLikeToArray(r, a);
        var t = {}.toString.call(r).slice(8, -1);
        return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0;
      }
    }
    function _wrapNativeSuper(t) {
      var r = "function" == typeof Map ? new Map() : void 0;
      return _wrapNativeSuper = function (t) {
        if (null === t || !_isNativeFunction(t)) return t;
        if ("function" != typeof t) throw new TypeError("Super expression must either be null or a function");
        if (void 0 !== r) {
          if (r.has(t)) return r.get(t);
          r.set(t, Wrapper);
        }
        function Wrapper() {
          return _construct(t, arguments, _getPrototypeOf(this).constructor);
        }
        return Wrapper.prototype = Object.create(t.prototype, {
          constructor: {
            value: Wrapper,
            enumerable: !1,
            writable: !0,
            configurable: !0
          }
        }), _setPrototypeOf(Wrapper, t);
      }, _wrapNativeSuper(t);
    }

    function relativeStrengthIndex () {
      var slidingWindow = _slidingWindow().period(14);
      var wildersSmoothing = function wildersSmoothing(values, prevAvg) {
        return prevAvg + (values[values.length - 1] - prevAvg) / values.length;
      };
      var downChange = function downChange(_ref) {
        var _ref2 = _slicedToArray(_ref, 2),
          prevClose = _ref2[0],
          close = _ref2[1];
        return prevClose < close ? 0 : prevClose - close;
      };
      var upChange = function upChange(_ref3) {
        var _ref4 = _slicedToArray(_ref3, 2),
          prevClose = _ref4[0],
          close = _ref4[1];
        return prevClose > close ? 0 : close - prevClose;
      };
      var updateAverage = function updateAverage(changes, prevAverage) {
        return prevAverage !== undefined ? wildersSmoothing(changes, prevAverage) : d3Array.mean(changes);
      };
      var makeAccumulator = function makeAccumulator() {
        var prevClose;
        var downChangesAvg;
        var upChangesAvg;
        return function (closes) {
          if (!closes) {
            if (prevClose !== undefined) {
              prevClose = NaN;
            }
            return undefined;
          }
          if (prevClose === undefined) {
            prevClose = closes[0];
            return undefined;
          }
          var closePairs = d3Array.pairs([prevClose].concat(_toConsumableArray(closes)));
          downChangesAvg = updateAverage(closePairs.map(downChange), downChangesAvg);
          upChangesAvg = updateAverage(closePairs.map(upChange), upChangesAvg);
          var rs = !isNaN(prevClose) ? upChangesAvg / downChangesAvg : NaN;
          return convertNaN(100 - 100 / (1 + rs));
        };
      };
      var rsi = function rsi(data) {
        var rsiAccumulator = makeAccumulator();
        slidingWindow.accumulator(rsiAccumulator);
        return slidingWindow(data);
      };
      rebind(rsi, slidingWindow, 'period', 'value');
      return rsi;
    }

    function movingAverage () {
      var slidingWindow = _slidingWindow().accumulator(function (values) {
        return values && d3Array.mean(values);
      });
      var movingAverage = function movingAverage(data) {
        return slidingWindow(data);
      };
      rebind(movingAverage, slidingWindow, 'period', 'value');
      return movingAverage;
    }

    function stochasticOscillator () {
      var closeValue = function closeValue(d, i) {
        return d.close;
      };
      var highValue = function highValue(d, i) {
        return d.high;
      };
      var lowValue = function lowValue(d, i) {
        return d.low;
      };
      var kWindow = _slidingWindow().period(5).defined(function (d) {
        return closeValue(d) != null && highValue(d) != null && lowValue(d) != null;
      }).accumulator(function (values) {
        var maxHigh = values && d3Array.max(values, highValue);
        var minLow = values && d3Array.min(values, lowValue);
        var kValue = values && 100 * (closeValue(values[values.length - 1]) - minLow) / (maxHigh - minLow);
        return convertNaN(kValue);
      });
      var dWindow = movingAverage().period(3);
      var stochastic = function stochastic(data) {
        var kValues = kWindow(data);
        var dValues = dWindow(kValues);
        return kValues.map(function (k, i) {
          return {
            k: k,
            d: dValues[i]
          };
        });
      };
      stochastic.closeValue = function () {
        if (!arguments.length) {
          return closeValue;
        }
        closeValue = arguments.length <= 0 ? undefined : arguments[0];
        return stochastic;
      };
      stochastic.highValue = function () {
        if (!arguments.length) {
          return highValue;
        }
        highValue = arguments.length <= 0 ? undefined : arguments[0];
        return stochastic;
      };
      stochastic.lowValue = function () {
        if (!arguments.length) {
          return lowValue;
        }
        lowValue = arguments.length <= 0 ? undefined : arguments[0];
        return stochastic;
      };
      rebindAll(stochastic, kWindow, includeMap({
        'period': 'kPeriod'
      }));
      rebindAll(stochastic, dWindow, includeMap({
        'period': 'dPeriod'
      }));
      return stochastic;
    }

    function forceIndex () {
      var volumeValue = function volumeValue(d, i) {
        return d.volume;
      };
      var closeValue = function closeValue(d, i) {
        return d.close;
      };
      var emaComputer = exponentialMovingAverage().period(13);
      var slidingWindow = _slidingWindow().period(2).defined(function (d) {
        return closeValue(d) != null && volumeValue(d) != null;
      }).accumulator(function (values) {
        return values && convertNaN((closeValue(values[1]) - closeValue(values[0])) * volumeValue(values[1]));
      });
      var force = function force(data) {
        var forceIndex = slidingWindow(data);
        return emaComputer(forceIndex);
      };
      force.volumeValue = function () {
        if (!arguments.length) {
          return volumeValue;
        }
        volumeValue = arguments.length <= 0 ? undefined : arguments[0];
        return force;
      };
      force.closeValue = function () {
        if (!arguments.length) {
          return closeValue;
        }
        closeValue = arguments.length <= 0 ? undefined : arguments[0];
        return force;
      };
      rebind(force, emaComputer, 'period');
      return force;
    }

    function envelope () {
      var factor = 0.1;
      var value = identity$5;
      var envelope = function envelope(data) {
        return data.map(function (d) {
          var lower = convertNaN(value(d) * (1.0 - factor));
          var upper = convertNaN(value(d) * (1.0 + factor));
          return {
            lower: lower,
            upper: upper
          };
        });
      };
      envelope.factor = function () {
        if (!arguments.length) {
          return factor;
        }
        factor = arguments.length <= 0 ? undefined : arguments[0];
        return envelope;
      };
      envelope.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        return envelope;
      };
      return envelope;
    }

    function elderRay () {
      var closeValue = function closeValue(d, i) {
        return d.close;
      };
      var highValue = function highValue(d, i) {
        return d.high;
      };
      var lowValue = function lowValue(d, i) {
        return d.low;
      };
      var emaComputer = exponentialMovingAverage().period(13);
      var elderRay = function elderRay(data) {
        emaComputer.value(closeValue);
        return d3Array.zip(data, emaComputer(data)).map(function (d) {
          var bullPower = convertNaN(highValue(d[0]) - d[1]);
          var bearPower = convertNaN(lowValue(d[0]) - d[1]);
          return {
            bullPower: bullPower,
            bearPower: bearPower
          };
        });
      };
      elderRay.closeValue = function () {
        if (!arguments.length) {
          return closeValue;
        }
        closeValue = arguments.length <= 0 ? undefined : arguments[0];
        return elderRay;
      };
      elderRay.highValue = function () {
        if (!arguments.length) {
          return highValue;
        }
        highValue = arguments.length <= 0 ? undefined : arguments[0];
        return elderRay;
      };
      elderRay.lowValue = function () {
        if (!arguments.length) {
          return lowValue;
        }
        lowValue = arguments.length <= 0 ? undefined : arguments[0];
        return elderRay;
      };
      rebind(elderRay, emaComputer, 'period');
      return elderRay;
    }

    function identity$4 () {
      var identity = {};
      identity.distance = function (start, end) {
        return end - start;
      };
      identity.offset = function (start, offset) {
        return start instanceof Date ? new Date(start.getTime() + offset) : start + offset;
      };
      identity.clampUp = function (d) {
        return d;
      };
      identity.clampDown = function (d) {
        return d;
      };
      identity.copy = function () {
        return identity;
      };
      return identity;
    }

    function tickFilter(ticks, discontinuityProvider) {
      var discontinuousTicks = ticks.map(discontinuityProvider.clampUp);
      if (discontinuousTicks.length !== new Set(discontinuousTicks.map(function (d) {
        return d === null || d === void 0 ? void 0 : d.valueOf();
      })).size) {
        console.warn('There are multiple ticks that fall within a discontinuity, which has led to them being rendered on top of each other. Consider using scale.ticks to explicitly specify the ticks for the scale.');
      }
      return discontinuousTicks;
    }

    function discontinuous(adaptedScale) {
      var _this = this;
      if (!arguments.length) {
        adaptedScale = d3Scale.scaleIdentity();
      }
      var discontinuityProvider = identity$4();
      var scale = function scale(value) {
        var domain = adaptedScale.domain();
        var range = adaptedScale.range();

        // The discontinuityProvider is responsible for determine the distance between two points
        // along a scale that has discontinuities (i.e. sections that have been removed).
        // the scale for the given point 'x' is calculated as the ratio of the discontinuous distance
        // over the domain of this axis, versus the discontinuous distance to 'x'
        var totalDomainDistance = discontinuityProvider.distance(domain[0], domain[1]);
        var distanceToX = discontinuityProvider.distance(domain[0], value);
        var ratioToX = distanceToX / totalDomainDistance;
        var scaledByRange = ratioToX * (range[1] - range[0]) + range[0];
        return scaledByRange;
      };
      scale.invert = function (x) {
        var domain = adaptedScale.domain();
        var range = adaptedScale.range();
        var ratioToX = (x - range[0]) / (range[1] - range[0]);
        var totalDomainDistance = discontinuityProvider.distance(domain[0], domain[1]);
        var distanceToX = ratioToX * totalDomainDistance;
        return discontinuityProvider.offset(domain[0], distanceToX);
      };
      scale.domain = function () {
        if (!arguments.length) {
          return adaptedScale.domain();
        }
        var newDomain = arguments.length <= 0 ? undefined : arguments[0];

        // clamp the upper and lower domain values to ensure they
        // do not fall within a discontinuity
        var domainLower = discontinuityProvider.clampUp(newDomain[0]);
        var domainUpper = discontinuityProvider.clampDown(newDomain[1]);
        adaptedScale.domain([domainLower, domainUpper]);
        return scale;
      };
      scale.nice = function () {
        adaptedScale.nice();
        var domain = adaptedScale.domain();
        var domainLower = discontinuityProvider.clampUp(domain[0]);
        var domainUpper = discontinuityProvider.clampDown(domain[1]);
        adaptedScale.domain([domainLower, domainUpper]);
        return scale;
      };
      scale.ticks = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        var ticks = adaptedScale.ticks.apply(_this, args);
        return tickFilter(ticks, discontinuityProvider);
      };
      scale.copy = function () {
        return discontinuous(adaptedScale.copy()).discontinuityProvider(discontinuityProvider.copy());
      };
      scale.discontinuityProvider = function () {
        if (!arguments.length) {
          return discontinuityProvider;
        }
        discontinuityProvider = arguments.length <= 0 ? undefined : arguments[0];
        return scale;
      };
      rebindAll(scale, adaptedScale, include('range', 'rangeRound', 'interpolate', 'clamp', 'tickFormat'));
      return scale;
    }

    var base$1 = function base(dayAccessor, intervalDay, intervalSaturday, intervalMonday) {
      // the indices returned by dayAccessor(date)
      var day = {
        sunday: 0,
        monday: 1,
        saturday: 6
      };
      var millisPerDay = 24 * 3600 * 1000;
      var millisPerWorkWeek = millisPerDay * 5;
      var millisPerWeek = millisPerDay * 7;
      var skipWeekends = {};
      var isWeekend = function isWeekend(date) {
        return dayAccessor(date) === 0 || dayAccessor(date) === 6;
      };
      skipWeekends.clampDown = function (date) {
        if (date && isWeekend(date)) {
          // round the date up to midnight
          var newDate = intervalDay.ceil(date);
          // then subtract the required number of days
          if (dayAccessor(newDate) === day.sunday) {
            return intervalDay.offset(newDate, -1);
          } else if (dayAccessor(newDate) === day.monday) {
            return intervalDay.offset(newDate, -2);
          } else {
            return newDate;
          }
        } else {
          return date;
        }
      };
      skipWeekends.clampUp = function (date) {
        if (date && isWeekend(date)) {
          // round the date down to midnight
          var newDate = intervalDay.floor(date);
          // then add the required number of days
          if (dayAccessor(newDate) === day.saturday) {
            return intervalDay.offset(newDate, 2);
          } else if (dayAccessor(newDate) === day.sunday) {
            return intervalDay.offset(newDate, 1);
          } else {
            return newDate;
          }
        } else {
          return date;
        }
      };

      // returns the number of included milliseconds (i.e. those which do not fall)
      // within discontinuities, along this scale
      skipWeekends.distance = function (startDate, endDate) {
        startDate = skipWeekends.clampUp(startDate);
        endDate = skipWeekends.clampDown(endDate);

        // move the start date to the end of week boundary
        var offsetStart = intervalSaturday.ceil(startDate);
        if (endDate < offsetStart) {
          return endDate.getTime() - startDate.getTime();
        }
        var msAdded = offsetStart.getTime() - startDate.getTime();

        // move the end date to the end of week boundary
        var offsetEnd = intervalSaturday.ceil(endDate);
        var msRemoved = offsetEnd.getTime() - endDate.getTime();

        // determine how many weeks there are between these two dates
        // round to account for DST transitions
        var weeks = Math.round((offsetEnd.getTime() - offsetStart.getTime()) / millisPerWeek);
        return weeks * millisPerWorkWeek + msAdded - msRemoved;
      };
      skipWeekends.offset = function (startDate, ms) {
        var date = isWeekend(startDate) ? skipWeekends.clampUp(startDate) : startDate;
        if (ms === 0) {
          return date;
        }
        var isNegativeOffset = ms < 0;
        var isPositiveOffset = ms > 0;
        var remainingms = ms;

        // move to the end of week boundary for a postive offset or to the start of a week for a negative offset
        var weekBoundary = isNegativeOffset ? intervalMonday.floor(date) : intervalSaturday.ceil(date);
        remainingms -= weekBoundary.getTime() - date.getTime();

        // if the distance to the boundary is greater than the number of ms
        // simply add the ms to the current date
        if (isNegativeOffset && remainingms > 0 || isPositiveOffset && remainingms < 0) {
          return new Date(date.getTime() + ms);
        }

        // skip the weekend for a positive offset
        date = isNegativeOffset ? weekBoundary : intervalDay.offset(weekBoundary, 2);

        // add all of the complete weeks to the date
        var completeWeeks = Math.floor(remainingms / millisPerWorkWeek);
        date = intervalDay.offset(date, completeWeeks * 7);
        remainingms -= completeWeeks * millisPerWorkWeek;

        // add the remaining time
        date = new Date(date.getTime() + remainingms);
        return date;
      };
      skipWeekends.copy = function () {
        return skipWeekends;
      };
      return skipWeekends;
    };
    var skipWeekends$1 = (function () {
      return base$1(function (date) {
        return date.getDay();
      }, d3Time.timeDay, d3Time.timeSaturday, d3Time.timeMonday);
    });

    var skipUtcWeekends = (function () {
      return base$1(function (date) {
        return date.getUTCDay();
      }, d3Time.utcDay, d3Time.utcSaturday, d3Time.utcMonday);
    });

    var provider = function provider() {
      for (var _len = arguments.length, ranges = new Array(_len), _key = 0; _key < _len; _key++) {
        ranges[_key] = arguments[_key];
      }
      var inRange = function inRange(number, range) {
        return number > range[0] && number < range[1];
      };
      var surroundsRange = function surroundsRange(inner, outer) {
        return inner[0] >= outer[0] && inner[1] <= outer[1];
      };
      var identity = {};
      identity.distance = function (start, end) {
        start = identity.clampUp(start);
        end = identity.clampDown(end);
        var surroundedRanges = ranges.filter(function (r) {
          return surroundsRange(r, [start, end]);
        });
        var rangeSizes = surroundedRanges.map(function (r) {
          return r[1] - r[0];
        });
        return end - start - rangeSizes.reduce(function (total, current) {
          return total + current;
        }, 0);
      };
      var add = function add(value, offset) {
        return value instanceof Date ? new Date(value.getTime() + offset) : value + offset;
      };
      identity.offset = function (location, offset) {
        if (offset > 0) {
          var currentLocation = identity.clampUp(location);
          var offsetRemaining = offset;
          while (offsetRemaining > 0) {
            var futureRanges = ranges.filter(function (r) {
              return r[0] > currentLocation;
            }).sort(function (a, b) {
              return a[0] - b[0];
            });
            if (futureRanges.length) {
              var nextRange = futureRanges[0];
              var delta = nextRange[0] - currentLocation;
              if (delta > offsetRemaining) {
                currentLocation = add(currentLocation, offsetRemaining);
                offsetRemaining = 0;
              } else {
                currentLocation = nextRange[1];
                offsetRemaining -= delta;
              }
            } else {
              currentLocation = add(currentLocation, offsetRemaining);
              offsetRemaining = 0;
            }
          }
          return currentLocation;
        } else {
          var _currentLocation = identity.clampDown(location);
          var _offsetRemaining = offset;
          while (_offsetRemaining < 0) {
            var _futureRanges = ranges.filter(function (r) {
              return r[1] < _currentLocation;
            }).sort(function (a, b) {
              return b[0] - a[0];
            });
            if (_futureRanges.length) {
              var _nextRange = _futureRanges[0];
              var _delta = _nextRange[1] - _currentLocation;
              if (_delta < _offsetRemaining) {
                _currentLocation = add(_currentLocation, _offsetRemaining);
                _offsetRemaining = 0;
              } else {
                _currentLocation = _nextRange[0];
                _offsetRemaining -= _delta;
              }
            } else {
              _currentLocation = add(_currentLocation, _offsetRemaining);
              _offsetRemaining = 0;
            }
          }
          return _currentLocation;
        }
      };
      identity.clampUp = function (d) {
        return ranges.reduce(function (value, range) {
          return inRange(value, range) ? range[1] : value;
        }, d);
      };
      identity.clampDown = function (d) {
        return ranges.reduce(function (value, range) {
          return inRange(value, range) ? range[0] : value;
        }, d);
      };
      identity.copy = function () {
        return identity;
      };
      return identity;
    };

    var millisPerDay = 24 * 3600 * 1000;
    var dayBoundary = "00:00:00.000";
    var SOD = 'SOD';
    var EOD = 'EOD';

    /**
     * Attempts to parse and format a time string into a fixed lenght string 'hh:mm:ss.fff'
     * @param {string} timeString - string representation of time 'hh:mm:ss.fff' e.g. '09:30' or '00:00:00.000'
     * @returns {int[]} array of parsed time components [hh, mm, ss, ms] or throws.
     */
    function standardiseTimeString(timeString) {
      if (arguments.length !== 1 || typeof timeString !== 'string') {
        throw 'Expected single argument of type string';
      }
      var isPositiveIntegerUpTo = function isPositiveIntegerUpTo(toCheck, upperBound) {
        if (!Number.isInteger(toCheck)) return false;
        return toCheck >= 0 && toCheck <= upperBound;
      };
      var result = [0, 0, 0, 0];
      var time_components = timeString.split(":");
      if (time_components.length < 2 || time_components.length > 3) {
        throw 'Expected an argument wiht 2 or 3 colon delimited parts.';
      }
      result[0] = isPositiveIntegerUpTo(parseInt(time_components[0], 10), 23) ? parseInt(time_components[0], 10) : function () {
        throw "'Hours' component must be an int between 0 and 23, but was '".concat(time_components[0], "'");
      }();
      result[1] = isPositiveIntegerUpTo(parseInt(time_components[1], 10), 59) ? parseInt(time_components[1], 10) : function () {
        throw "'Minutes' component must be an int between 0 and 59, but was '".concat(time_components[1], "'");
      }();
      if (time_components.length === 3) {
        var ms_components = time_components[2].split(".").map(function (x) {
          return parseInt(x, 10);
        });
        result[2] = isPositiveIntegerUpTo(ms_components[0], 59) ? ms_components[0] : function () {
          throw "'Seconds' component must be an int between 0 and 59, but was '".concat(ms_components[0], "'");
        }();
        if (ms_components.length === 2) {
          result[3] = isPositiveIntegerUpTo(ms_components[1], 999) ? ms_components[1] : function () {
            throw "'Miliseconds' component must be an int between 0 and 999, but was '".concat(ms_components[1], "'");
          }();
        }
      }
      return "".concat(result[0].toString(10).padStart(2, '0'), ":").concat(result[1].toString(10).padStart(2, '0'), ":").concat(result[2].toString(10).padStart(2, '0'), ".").concat(result[3].toString(10).padStart(3, '0'));
    }

    /**
     * @typedef { Object } nonTradingTimeRange
     * @property { string } startTime - Start time string with fixed format 'hh:mm:ss.fff'
     * @property { string } endTime - End time string with fixed format 'hh:mm:ss.fff'
     * @property { int } lenghtInMs - Absolute length in MS i.e. only valid on non-Daylight saving boundaries
     */

    /**
     * Represents a single continous Non-Trading time interval within a single day. You must denote day boundries as:
     * SOD - start of day 
     * EOD  - end of day
     * @constructor
     * @param { string[] } timeRangeTuple - Time range as a tuple of time strings e.g. ["07:45", "08:30"), ["SOD", "08:30:20") or ["19:00:45.500", "EOD").
     * @param { import('./dateTimeUtility').DateTimeUtility } dateTimeUtility
     * @returns { nonTradingTimeRange }
     */
    function nonTradingTimeRange(timeRangeTuple, dateTimeUtility) {
      if (arguments.length != 2 || !Array.isArray(timeRangeTuple) || timeRangeTuple.length !== 2 || typeof timeRangeTuple[0] !== 'string' || typeof timeRangeTuple[1] !== 'string') {
        throw "Expected argument is a single string[] of length 2.";
      }
      if (timeRangeTuple[0] === SOD) {
        timeRangeTuple[0] = dayBoundary;
      }
      if (timeRangeTuple[1] === EOD) {
        timeRangeTuple[1] = dayBoundary;
      }
      var startTime = standardiseTimeString(timeRangeTuple[0]);
      var endTime = standardiseTimeString(timeRangeTuple[1]);
      if (endTime !== dayBoundary && startTime > endTime) {
        throw "Time range start time '".concat(startTime, "' must be before end time '").concat(endTime, "' or both must equal ").concat(dayBoundary);
      }
      var lenghtInMs = dateTimeUtility.setTime(new Date(endTime === dayBoundary ? millisPerDay : 0), endTime) - dateTimeUtility.setTime(new Date(0), startTime);
      var instance = {
        startTime: startTime,
        endTime: endTime,
        lenghtInMs: lenghtInMs
      };

      /**
       * Returns if given date's time portion is within this discontinuity time range instance
       * @param { Date } date - date
       * @returns { boolean }
       */
      instance.isInRange = function (date) {
        var time = dateTimeUtility.getTimeString(date);
        if (instance.startTime <= time && (instance.endTime === dayBoundary || instance.endTime > time)) {
          return true;
        }
        return false;
      };
      return instance;
    }

    /**
     * Represents a Trading day
     * @param { string[][] } rawDiscontinuityTimeRanges - Array of time range tuples e.g. [["07:45", "08:30"), ["19:00:45.500", "EOD")]
     * @param { import('./dateTimeUtility').DateTimeUtility } dateTimeUtility
     */
    var tradingDay = function tradingDay(rawDiscontinuityTimeRanges, dateTimeUtility) {
      var nonTradingTimeRanges = rawDiscontinuityTimeRanges.map(function (rawRange) {
        return nonTradingTimeRange(rawRange, dateTimeUtility);
      }).sort(function (a, b) {
        return a.startTime < b.startTime ? -1 : a.startTime > b.startTime ? 1 : 0;
      });
      var totalTradingTimeInMiliseconds = millisPerDay - nonTradingTimeRanges.reduce(function (total, range) {
        return total + range.lenghtInMs;
      }, 0);
      var totalTradingMillisecondsBetween = function totalTradingMillisecondsBetween(intervalStart, intervalEnd) {
        if (intervalStart.getTime() === intervalEnd.getTime()) {
          return 0;
        }

        // ensure arguments are on the same day or intervalEnd is the next day boundary
        if (dateTimeUtility.dayInterval(intervalStart).getTime() !== dateTimeUtility.dayInterval(intervalEnd).getTime() && dateTimeUtility.getStartOfNextDay(intervalStart).getTime() !== intervalEnd.getTime()) {
          throw "tradingDay.totalTradingMillisecondsBetween arguments must be on the same day or intervalEnd must be the start of the next day instead: intervalStart: '".concat(intervalStart, "'; intervalEnd: '").concat(intervalEnd, "'");
        }
        var total = 0;
        var relevantDiscontinuityRanges = nonTradingTimeRanges.filter(function (range) {
          return range.endTime === dayBoundary || dateTimeUtility.setTime(intervalStart, range.endTime) >= intervalStart;
        });
        var _iterator = _createForOfIteratorHelper(relevantDiscontinuityRanges),
          _step;
        try {
          for (_iterator.s(); !(_step = _iterator.n()).done;) {
            var nonTradingRange = _step.value;
            var nonTradingStart = dateTimeUtility.setTime(intervalStart, nonTradingRange.startTime);
            var nonTradingEnd = nonTradingRange.endTime === dayBoundary ? dateTimeUtility.getStartOfNextDay(intervalStart) : dateTimeUtility.setTime(intervalStart, nonTradingRange.endTime);

            // both intervalStart and intervalEnd are before the start of this non-trading range
            if (intervalStart < nonTradingStart && intervalEnd < nonTradingStart) {
              return total + dateTimeUtility.msInterval.count(intervalStart, intervalEnd);
            }

            // intervalStart is before the start of this non-trading time range
            if (intervalStart < nonTradingStart) {
              total += dateTimeUtility.msInterval.count(intervalStart, nonTradingStart);
            }

            // interval ends within non-trading range
            if (intervalEnd < nonTradingEnd) {
              return total;
            }

            // set interval start to the end of non-trading range
            intervalStart = nonTradingEnd;
          }

          // add any interval time still left after iterating through all non-trading ranges
        } catch (err) {
          _iterator.e(err);
        } finally {
          _iterator.f();
        }
        return total + dateTimeUtility.msInterval.count(intervalStart, intervalEnd);
      };
      var offset = function offset(date, ms) {
        if (ms === 0) {
          return [date, ms];
        }
        var offsetDate = dateTimeUtility.msInterval.offset(date, ms);
        var nonTradingRanges = ms > 0 ? nonTradingTimeRanges.filter(function (range) {
          return dateTimeUtility.setTime(date, range.startTime) >= date;
        }) : nonTradingTimeRanges.filter(function (range) {
          return dateTimeUtility.setTime(date, range.startTime) < date;
        }).reverse();
        if (nonTradingRanges.length === 0) {
          return [dateTimeUtility.msInterval.offset(date, ms), 0];
        }
        if (ms > 0) {
          var _iterator2 = _createForOfIteratorHelper(nonTradingRanges),
            _step2;
          try {
            for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
              var nonTradingRange = _step2.value;
              var rangeStart = dateTimeUtility.setTime(date, nonTradingRange.startTime);
              if (rangeStart <= offsetDate) {
                // offsetDate is within non-trading range
                ms -= dateTimeUtility.msInterval.count(date, rangeStart);
                date = nonTradingRange.endTime === dayBoundary ? dateTimeUtility.getStartOfNextDay(date) : dateTimeUtility.setTime(date, nonTradingRange.endTime);
                offsetDate = dateTimeUtility.msInterval.offset(date, ms);
              }
            }
          } catch (err) {
            _iterator2.e(err);
          } finally {
            _iterator2.f();
          }
          ms -= dateTimeUtility.msInterval.count(date, offsetDate);
        } else {
          var _iterator3 = _createForOfIteratorHelper(nonTradingRanges),
            _step3;
          try {
            for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
              var _nonTradingRange = _step3.value;
              var endTime = _nonTradingRange.endTime === dayBoundary ? dateTimeUtility.getStartOfNextDay(date) : dateTimeUtility.setTime(date, _nonTradingRange.endTime);
              if (offsetDate < endTime) {
                // offsetDate is within non-trading range
                ms += dateTimeUtility.msInterval.count(endTime, date) + 1;
                date = dateTimeUtility.msInterval.offset(dateTimeUtility.setTime(date, _nonTradingRange.startTime), -1);
                offsetDate = dateTimeUtility.msInterval.offset(date, ms);
              }
            }
          } catch (err) {
            _iterator3.e(err);
          } finally {
            _iterator3.f();
          }
          ms += dateTimeUtility.msInterval.count(offsetDate, date);
        }
        if (ms !== 0) {
          throw 'tradingDay.offset was called with an offset that spans more than a day';
        }
        return [offsetDate, ms];
      };
      return {
        totalTradingTimeInMiliseconds: totalTradingTimeInMiliseconds,
        nonTradingTimeRanges: nonTradingTimeRanges,
        totalTradingMillisecondsBetween: totalTradingMillisecondsBetween,
        offset: offset
      };
    };

    /**
     * Object that helps with working with time strings and dates
     * @typedef { Object } DateTimeUtility
     * @property { function(Date): string } getTimeString - get's the time string for date as 'hh:mm:ss.fff'
     * @property { function(Date , string, number): Date } setTime - set the time  for date as
     * @property { function(Date): Date } getStartOfNextDay - returns the start of the next day i.e. 00:00:00.000
     * @property { function(Date): Date } getEndOfPreviousDay - returns the 'End' of the previous day i.e. one ms before midnight
     */

    /**
     * 
     * @param {function(Date, number, number, number, number): Date } setTimeForDate - sets a time on a Date object given hh, mm, ss & ms time compononets
     * @param {function(Date): number } getDay 
     * @param {function(Date): number[] } getTimeComponentArray 
     * @param {function} dayInterval - d3-time timeDay or utcDay
     * @param {function} msInterval - d3-time timeMillisecond or utcMillisecond
      * @returns {DateTimeUtility}
     */
    var dateTimeUtility = function dateTimeUtility(setTimeForDate, getDay, getTimeComponentArray, dayInterval, msInterval) {
      var utility = {};
      utility.getTimeComponentArrayFromString = function (timeString) {
        return [timeString.slice(0, 2), timeString.slice(3, 5), timeString.slice(6, 8), timeString.slice(9, 12)];
      };
      /**
          * Returns the local time part of a given Date instance as 'hh:mm:ss.fff'
          * @param {Date} date - Data instance
          * @returns {string} time string.
          */
      utility.getTimeString = function (date) {
        var _getTimeComponentArra = getTimeComponentArray(date).map(function (x) {
            return x.toString(10).padStart(2, '0');
          }),
          _getTimeComponentArra2 = _slicedToArray(_getTimeComponentArra, 4),
          hh = _getTimeComponentArra2[0],
          mm = _getTimeComponentArra2[1],
          ss = _getTimeComponentArra2[2],
          ms = _getTimeComponentArra2[3];
        return "".concat(hh, ":").concat(mm, ":").concat(ss, ".").concat(ms.padStart(3, '0'));
      };

      /**
       * Returns the combined local date and time string
       * @param {Date} date - Data instance
       * @param {string} timeString - string as 'hh:mm:ss.fff'
       * @param {number} offsetInmilliSeconds - additional offset in millisends. Default = 0; e.g. -1 is one millisecond before time specified by timeString;
       * @returns {Date} - combined date and time.
       */
      utility.setTime = function (date, timeString) {
        var offsetInmilliSeconds = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 0;
        var _utility$getTimeCompo = utility.getTimeComponentArrayFromString(timeString),
          _utility$getTimeCompo2 = _slicedToArray(_utility$getTimeCompo, 4),
          hh = _utility$getTimeCompo2[0],
          mm = _utility$getTimeCompo2[1],
          ss = _utility$getTimeCompo2[2],
          ms = _utility$getTimeCompo2[3];
        return msInterval.offset(setTimeForDate(date, hh, mm, ss, ms), offsetInmilliSeconds);
      };

      /**
       * Returns the start of the next day i.e. 00:00:00.000
       * @param {Date} date - Data instance
       * @returns {Date}.
       */
      utility.getStartOfNextDay = function (date) {
        return dayInterval.offset(dayInterval.floor(date), 1);
      };

      /**
       * Returns the end of the previous day (1ms before midnight) i.e.  23:59:59.999
       * @param {Date} date - Data instance
       * @returns {Date}.
       */
      utility.getEndOfPreviousDay = function (date) {
        return msInterval.offset(dayInterval.floor(date), -1);
      };
      utility.dayInterval = dayInterval;
      utility.msInterval = msInterval;
      utility.getDay = getDay;
      return utility;
    };

    var localDateTimeUtility = dateTimeUtility(function (date, hh, mm, ss, ms) {
      return new Date(date.getFullYear(), date.getMonth(), date.getDate(), hh, mm, ss, ms);
    }, function (date) {
      return date.getDay();
    }, function (date) {
      return [date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds()];
    }, d3Time.timeDay, d3Time.timeMillisecond);

    /**
     * Discontinuity provider implemenation that works with 'non-trading' periods during a trading day
     * @typedef { Object } WeeklyPatternDiscontinuityProvider
     * @property { function(Date): Date } clampUp - When given a value, if it falls within a discontinuity (i.e. an excluded domain range) it should be shifted forwards to the discontinuity boundary. Otherwise, it should be returned unchanged.
     * @property { function(Date): Date } clampDown - When given a value, if it falls within a discontinuity it should be shifted backwards to the discontinuity boundary. Otherwise, it should be returned unchanged.
     * @property { function(Date, Date): number } distance - When given a pair of values, this function returns the distance between the, in domain units, minus any discontinuities. discontinuities.
     * @property { function(Date, number): Date } offset - When given a value and an offset, the value should be advanced by the offset value, skipping any discontinuities, to return the final value.
     * @property { function(): WeeklyPatternDiscontinuityProvider } copy - Creates a copy of the discontinuity provider.
      */

    /**
     * Creates WeeklyPatternDiscontinuityProvider
     * @param {Object} nonTradingPattern - contains raw 'non-trading' time ranges for each day of the week
     * @param {DateTimeUtility} dateTimeUtility - uses local or utc dates
     * @returns { WeeklyPatternDiscontinuityProvider } WeeklyPatternDiscontinuityProvider
     */
    var base = function base(nonTradingPattern, dateTimeUtility) {
      var getDayPatternOrDefault = function getDayPatternOrDefault(day) {
        return nonTradingPattern[day] === undefined ? [] : nonTradingPattern[day];
      };
      var tradingDays = [tradingDay(getDayPatternOrDefault('Sunday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Monday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Tuesday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Wednesday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Thursday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Friday'), dateTimeUtility), tradingDay(getDayPatternOrDefault('Saturday'), dateTimeUtility)];
      var totalTradingWeekMilliseconds = tradingDays.reduce(function (total, tradingDay) {
        return total + tradingDay.totalTradingTimeInMiliseconds;
      }, 0);
      if (totalTradingWeekMilliseconds === 0) {
        throw 'Trading pattern must yield at least 1 ms of trading time';
      }
      var instance = {
        tradingDays: tradingDays,
        totalTradingWeekMilliseconds: totalTradingWeekMilliseconds
      };

      /**
       * When given a value falls within a discontinuity (i.e. an excluded domain range) it should be shifted forwards to the discontinuity boundary. 
       * Otherwise, it should be returns unchanged.
       * @param {Date} date - date to clamp up
       * @returns {Date}
       */
      instance.clampUp = function (date) {
        var tradingDay = tradingDays[dateTimeUtility.getDay(date)];
        var _iterator = _createForOfIteratorHelper(tradingDay.nonTradingTimeRanges),
          _step;
        try {
          for (_iterator.s(); !(_step = _iterator.n()).done;) {
            var range = _step.value;
            if (range.isInRange(date)) {
              return range.endTime === dayBoundary ? instance.clampUp(dateTimeUtility.getStartOfNextDay(date)) : dateTimeUtility.setTime(date, range.endTime);
            }
          }
        } catch (err) {
          _iterator.e(err);
        } finally {
          _iterator.f();
        }
        return date;
      };

      /** 
       * When given a value, if it falls within a discontinuity it should be shifted backwards to the discontinuity boundary. Otherwise, it should be returned unchanged.
       * @param {Date} date - date to clamp down
       * @returns {Date}
      */
      instance.clampDown = function (date) {
        var tradingDay = tradingDays[dateTimeUtility.getDay(date)];
        var _iterator2 = _createForOfIteratorHelper(tradingDay.nonTradingTimeRanges),
          _step2;
        try {
          for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
            var range = _step2.value;
            if (range.isInRange(date)) {
              return range.startTime === dayBoundary ? instance.clampDown(dateTimeUtility.getEndOfPreviousDay(date)) : dateTimeUtility.setTime(date, range.startTime, -1);
            }
          }
        } catch (err) {
          _iterator2.e(err);
        } finally {
          _iterator2.f();
        }
        return date;
      };

      /**
       * When given a pair of values, this function returns the distance between the, in domain units, minus any discontinuities. discontinuities.
       * @param {Date} startDate 
       * @param {Date} endDate 
       * @returns {number} - the number of milliseconds between the dates
       */
      instance.distance = function (startDate, endDate) {
        if (startDate.getTime() === endDate.getTime()) {
          return 0;
        }
        var _ref = startDate <= endDate ? [startDate, endDate, 1] : [endDate, startDate, -1],
          _ref2 = _slicedToArray(_ref, 3),
          start = _ref2[0],
          end = _ref2[1],
          factor = _ref2[2];

        // same day distance
        if (dateTimeUtility.dayInterval(start).getTime() === dateTimeUtility.dayInterval(end).getTime()) {
          return instance.tradingDays[dateTimeUtility.getDay(start)].totalTradingMillisecondsBetween(start, end);
        }

        // combine any trading time left in the day after startDate 
        // and any trading time from midnight up until the endDate
        var total = instance.tradingDays[dateTimeUtility.getDay(start)].totalTradingMillisecondsBetween(start, dateTimeUtility.dayInterval.offset(dateTimeUtility.dayInterval(start), 1)) + instance.tradingDays[dateTimeUtility.getDay(end)].totalTradingMillisecondsBetween(dateTimeUtility.dayInterval(end), end);

        // startDate and endDate are consecutive days    
        if (dateTimeUtility.dayInterval.count(start, end) === 1) {
          return total;
        }

        // move the start date to following day
        start = dateTimeUtility.dayInterval.offset(dateTimeUtility.dayInterval(start), 1);
        // floor endDate to remove 'time component'
        end = dateTimeUtility.dayInterval(end);
        return factor * dateTimeUtility.dayInterval.range(start, end).reduce(function (runningTotal, currentDay, currentIndex, arr) {
          var nextDay = currentIndex < arr.length - 1 ? arr[currentIndex + 1] : dateTimeUtility.dayInterval.offset(currentDay, 1);
          var isDstBoundary = nextDay - currentDay !== millisPerDay;
          var tradingDay = instance.tradingDays[dateTimeUtility.getDay(currentDay)];
          return runningTotal += isDstBoundary ? tradingDay.totalTradingMillisecondsBetween(currentDay, nextDay) : tradingDay.totalTradingTimeInMiliseconds;
        }, total);
      };

      /**
       * When given a value and an offset in milliseconds, the value should be advanced by the offset value, skipping any discontinuities, to return the final value.
       * @param {Date} date 
       * @param {number} ms 
       */
      instance.offset = function (date, ms) {
        date = ms >= 0 ? instance.clampUp(date) : instance.clampDown(date);
        var isDstBoundary = function isDstBoundary(d) {
          return dateTimeUtility.dayInterval.offset(d) - dateTimeUtility.dayInterval(d) !== millisPerDay;
        };
        var moveToDayBoundary = function moveToDayBoundary(tradingDay, date, ms) {
          if (ms < 0) {
            var dateFloor = dateTimeUtility.dayInterval(date);
            var distanceToStartOfDay = tradingDay.totalTradingMillisecondsBetween(dateFloor, date);
            return Math.abs(ms) <= distanceToStartOfDay ? tradingDay.offset(date, ms) : [instance.clampDown(dateTimeUtility.msInterval.offset(dateFloor, -1)), ms + distanceToStartOfDay + 1];
          } else {
            var nextDate = dateTimeUtility.getStartOfNextDay(date);
            var distanceToDayBoundary = tradingDay.totalTradingMillisecondsBetween(date, nextDate);
            return ms < distanceToDayBoundary ? tradingDay.offset(date, ms) : [instance.clampUp(nextDate), ms - distanceToDayBoundary];
          }
        };
        if (ms === 0) return date;
        var moveDateDelegate = ms < 0 ? function (date, remainingMs, tradingDayMs) {
          return [instance.clampDown(dateTimeUtility.dayInterval.offset(date, -1)), remainingMs + tradingDayMs];
        } : function (date, remainingMs, tradingDayMs) {
          return [instance.clampUp(dateTimeUtility.dayInterval.offset(date)), remainingMs - tradingDayMs];
        };
        var tradingDay = instance.tradingDays[dateTimeUtility.getDay(date)];
        var _moveToDayBoundary = moveToDayBoundary(tradingDay, date, ms);
        var _moveToDayBoundary2 = _slicedToArray(_moveToDayBoundary, 2);
        date = _moveToDayBoundary2[0];
        ms = _moveToDayBoundary2[1];
        while (ms !== 0) {
          tradingDay = instance.tradingDays[dateTimeUtility.getDay(date)];
          if (isDstBoundary(date)) {
            var _moveToDayBoundary3 = moveToDayBoundary(tradingDay, date, ms);
            var _moveToDayBoundary4 = _slicedToArray(_moveToDayBoundary3, 2);
            date = _moveToDayBoundary4[0];
            ms = _moveToDayBoundary4[1];
          } else {
            var _ref3 = Math.abs(ms) >= tradingDay.totalTradingTimeInMiliseconds ? moveDateDelegate(date, ms, tradingDay.totalTradingTimeInMiliseconds) : moveToDayBoundary(tradingDay, date, ms);
            var _ref4 = _slicedToArray(_ref3, 2);
            date = _ref4[0];
            ms = _ref4[1];
          }
        }
        return date;
      };
      instance.copy = function () {
        return instance;
      };
      return instance;
    };
    var skipWeeklyPattern = (function (nonTradingHoursPattern) {
      return base(nonTradingHoursPattern, localDateTimeUtility);
    });

    var utcDateTimeUtility = dateTimeUtility(function (date, hh, mm, ss, ms) {
      return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), hh, mm, ss, ms));
    }, function (date) {
      return date.getUTCDay();
    }, function (date) {
      return [date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds(), date.getUTCMilliseconds()];
    }, d3Time.utcDay, d3Time.utcMillisecond);
    var skipUtcWeeklyPattern = (function (nonTradingUtcHoursPattern) {
      return base(nonTradingUtcHoursPattern, utcDateTimeUtility);
    });

    function linearExtent () {
      var accessors = [function (d) {
        return d;
      }];
      var pad = [0, 0];
      var padUnit = 'percent';
      var symmetricalAbout = null;
      var include = [];
      var instance = function instance(data) {
        var values = new Array(data.length);
        var _iterator = _createForOfIteratorHelper(accessors),
          _step;
        try {
          for (_iterator.s(); !(_step = _iterator.n()).done;) {
            var accessor = _step.value;
            for (var i = 0; i < data.length; i++) {
              var value = accessor(data[i], i);
              if (Array.isArray(value)) {
                values.push.apply(values, _toConsumableArray(value));
              } else {
                values.push(value);
              }
            }
          }
        } catch (err) {
          _iterator.e(err);
        } finally {
          _iterator.f();
        }
        var extent = [d3Array.min(values), d3Array.max(values)];
        extent[0] = extent[0] == null ? d3Array.min(include) : d3Array.min([extent[0]].concat(_toConsumableArray(include)));
        extent[1] = extent[1] == null ? d3Array.max(include) : d3Array.max([extent[1]].concat(_toConsumableArray(include)));
        if (symmetricalAbout != null) {
          var halfRange = Math.max(Math.abs(extent[1] - symmetricalAbout), Math.abs(extent[0] - symmetricalAbout));
          extent[0] = symmetricalAbout - halfRange;
          extent[1] = symmetricalAbout + halfRange;
        }
        switch (padUnit) {
          case 'domain':
            {
              extent[0] -= pad[0];
              extent[1] += pad[1];
              break;
            }
          case 'percent':
            {
              var delta = extent[1] - extent[0];
              extent[0] -= pad[0] * delta;
              extent[1] += pad[1] * delta;
              break;
            }
          default:
            throw new Error("Unknown padUnit: ".concat(padUnit));
        }
        return extent;
      };
      instance.accessors = function () {
        if (!arguments.length) {
          return accessors;
        }
        accessors = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.pad = function () {
        if (!arguments.length) {
          return pad;
        }
        pad = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.padUnit = function () {
        if (!arguments.length) {
          return padUnit;
        }
        padUnit = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.include = function () {
        if (!arguments.length) {
          return include;
        }
        include = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.symmetricalAbout = function () {
        if (!arguments.length) {
          return symmetricalAbout;
        }
        symmetricalAbout = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      return instance;
    }

    function time () {
      var accessors = [];
      var pad = [0, 0];
      var padUnit = 'percent';
      var symmetricalAbout = null;
      var include = [];
      var extent = linearExtent();
      var valueOf = function valueOf(date) {
        return date != null ? date.valueOf() : null;
      };
      var instance = function instance(data) {
        var adaptedAccessors = accessors.map(function (accessor) {
          return function () {
            var value = accessor.apply(void 0, arguments);
            return Array.isArray(value) ? value.map(valueOf) : valueOf(value);
          };
        });
        extent.accessors(adaptedAccessors).pad(pad).padUnit(padUnit).symmetricalAbout(symmetricalAbout != null ? symmetricalAbout.valueOf() : null).include(include.map(function (date) {
          return date.valueOf();
        }));
        return extent(data).map(function (value) {
          return new Date(value);
        });
      };
      instance.accessors = function () {
        if (!arguments.length) {
          return accessors;
        }
        accessors = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.pad = function () {
        if (!arguments.length) {
          return pad;
        }
        pad = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.padUnit = function () {
        if (!arguments.length) {
          return padUnit;
        }
        padUnit = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.include = function () {
        if (!arguments.length) {
          return include;
        }
        include = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.symmetricalAbout = function () {
        if (!arguments.length) {
          return symmetricalAbout;
        }
        symmetricalAbout = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      return instance;
    }

    function geometricBrownianMotion () {
      var period = 1;
      var steps = 20;
      var mu = 0.1;
      var sigma = 0.1;
      var random = d3Random.randomNormal();
      var geometricBrownianMotion = function geometricBrownianMotion() {
        var value = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
        var timeStep = period / steps;
        var pathData = [];
        for (var i = 0; i < steps + 1; i++) {
          pathData.push(value);
          var increment = random() * Math.sqrt(timeStep) * sigma + (mu - sigma * sigma / 2) * timeStep;
          value = value * Math.exp(increment);
        }
        return pathData;
      };
      geometricBrownianMotion.period = function () {
        if (!arguments.length) {
          return period;
        }
        period = arguments.length <= 0 ? undefined : arguments[0];
        return geometricBrownianMotion;
      };
      geometricBrownianMotion.steps = function () {
        if (!arguments.length) {
          return steps;
        }
        steps = arguments.length <= 0 ? undefined : arguments[0];
        return geometricBrownianMotion;
      };
      geometricBrownianMotion.mu = function () {
        if (!arguments.length) {
          return mu;
        }
        mu = arguments.length <= 0 ? undefined : arguments[0];
        return geometricBrownianMotion;
      };
      geometricBrownianMotion.sigma = function () {
        if (!arguments.length) {
          return sigma;
        }
        sigma = arguments.length <= 0 ? undefined : arguments[0];
        return geometricBrownianMotion;
      };
      geometricBrownianMotion.random = function () {
        if (!arguments.length) {
          return random;
        }
        random = arguments.length <= 0 ? undefined : arguments[0];
        return geometricBrownianMotion;
      };
      return geometricBrownianMotion;
    }

    function functor$5(v) {
      return typeof v === 'function' ? v : function () {
        return v;
      };
    }

    function financial () {
      var startDate = new Date();
      var startPrice = 100;
      var interval = d3Time.timeDay;
      var intervalStep = 1;
      var unitInterval = d3Time.timeYear;
      var unitIntervalStep = 1;
      var filter = null;
      var volume = function volume() {
        var normal = d3Random.randomNormal(1, 0.1);
        return Math.ceil(normal() * 1000);
      };
      var gbm = geometricBrownianMotion();
      var getOffsetPeriod = function getOffsetPeriod(date) {
        var unitMilliseconds = unitInterval.offset(date, unitIntervalStep) - date;
        return (interval.offset(date, intervalStep) - date) / unitMilliseconds;
      };
      var calculateOHLC = function calculateOHLC(start, price) {
        var period = getOffsetPeriod(start);
        var prices = gbm.period(period)(price);
        var ohlc = {
          date: start,
          open: prices[0],
          high: Math.max.apply(Math, prices),
          low: Math.min.apply(Math, prices),
          close: prices[gbm.steps()]
        };
        ohlc.volume = volume(ohlc);
        return ohlc;
      };
      var getNextDatum = function getNextDatum(ohlc) {
        var date, price, filtered;
        do {
          date = ohlc ? interval.offset(ohlc.date, intervalStep) : new Date(startDate.getTime());
          price = ohlc ? ohlc.close : startPrice;
          ohlc = calculateOHLC(date, price);
          filtered = filter && !filter(ohlc);
        } while (filtered);
        return ohlc;
      };
      var makeStream = function makeStream() {
        var latest;
        var stream = {};
        stream.next = function () {
          var ohlc = getNextDatum(latest);
          latest = ohlc;
          return ohlc;
        };
        stream.take = function (numPoints) {
          return stream.until(function (d, i) {
            return !numPoints || numPoints < 0 || i === numPoints;
          });
        };
        stream.until = function (comparison) {
          var data = [];
          var index = 0;
          var ohlc = getNextDatum(latest);
          var compared = comparison && !comparison(ohlc, index);
          while (compared) {
            data.push(ohlc);
            latest = ohlc;
            ohlc = getNextDatum(latest);
            index += 1;
            compared = comparison && !comparison(ohlc, index);
          }
          return data;
        };
        return stream;
      };
      var financial = function financial(numPoints) {
        return makeStream().take(numPoints);
      };
      financial.stream = makeStream;
      if (typeof Symbol !== 'function' || _typeof(Symbol.iterator) !== 'symbol') {
        throw new Error('d3fc-random-data depends on Symbol. Make sure that you load a polyfill in older browsers. See README.');
      }
      financial[Symbol.iterator] = function () {
        var stream = makeStream();
        return {
          next: function next() {
            return {
              value: stream.next(),
              done: false
            };
          }
        };
      };
      financial.startDate = function () {
        if (!arguments.length) {
          return startDate;
        }
        startDate = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.startPrice = function () {
        if (!arguments.length) {
          return startPrice;
        }
        startPrice = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.interval = function () {
        if (!arguments.length) {
          return interval;
        }
        interval = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.intervalStep = function () {
        if (!arguments.length) {
          return intervalStep;
        }
        intervalStep = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.unitInterval = function () {
        if (!arguments.length) {
          return unitInterval;
        }
        unitInterval = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.unitIntervalStep = function () {
        if (!arguments.length) {
          return unitIntervalStep;
        }
        unitIntervalStep = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.filter = function () {
        if (!arguments.length) {
          return filter;
        }
        filter = arguments.length <= 0 ? undefined : arguments[0];
        return financial;
      };
      financial.volume = function () {
        if (!arguments.length) {
          return volume;
        }
        volume = functor$5(arguments.length <= 0 ? undefined : arguments[0]);
        return financial;
      };
      rebindAll(financial, gbm);
      return financial;
    }

    function skipWeekends (datum) {
      var day = datum.date.getDay();
      return !(day === 0 || day === 6);
    }

    // https://docs.gdax.com/#market-data
    function gdax () {
      var product = 'BTC-USD';
      var start = null;
      var end = null;
      var granularity = null;
      var gdax = function gdax() {
        var params = [];
        if (start != null) {
          params.push('start=' + start.toISOString());
        }
        if (end != null) {
          params.push('end=' + end.toISOString());
        }
        if (granularity != null) {
          params.push('granularity=' + granularity);
        }
        var url = 'https://api.gdax.com/products/' + product + '/candles?' + params.join('&');
        return d3Fetch.json(url).then(function (data) {
          return data.map(function (d) {
            return {
              date: new Date(d[0] * 1000),
              open: d[3],
              high: d[2],
              low: d[1],
              close: d[4],
              volume: d[5]
            };
          });
        });
      };
      gdax.product = function (x) {
        if (!arguments.length) {
          return product;
        }
        product = x;
        return gdax;
      };
      gdax.start = function (x) {
        if (!arguments.length) {
          return start;
        }
        start = x;
        return gdax;
      };
      gdax.end = function (x) {
        if (!arguments.length) {
          return end;
        }
        end = x;
        return gdax;
      };
      gdax.granularity = function (x) {
        if (!arguments.length) {
          return granularity;
        }
        granularity = x;
        return gdax;
      };
      return gdax;
    }

    function bucket () {
      var bucketSize = 10;
      var bucket = function bucket(data) {
        return bucketSize <= 1 ? data.map(function (d) {
          return [d];
        }) : d3Array.range(0, Math.ceil(data.length / bucketSize)).map(function (i) {
          return data.slice(i * bucketSize, (i + 1) * bucketSize);
        });
      };
      bucket.bucketSize = function (x) {
        if (!arguments.length) {
          return bucketSize;
        }
        bucketSize = x;
        return bucket;
      };
      return bucket;
    }

    function largestTriangleOneBucket () {
      var dataBucketer = bucket();
      var x = function x(d) {
        return d;
      };
      var y = function y(d) {
        return d;
      };
      var largestTriangleOneBucket = function largestTriangleOneBucket(data) {
        if (dataBucketer.bucketSize() >= data.length) {
          return data;
        }
        var pointAreas = calculateAreaOfPoints(data);
        var pointAreaBuckets = dataBucketer(pointAreas);
        var buckets = dataBucketer(data.slice(1, data.length - 1));
        var subsampledData = buckets.map(function (thisBucket, i) {
          var pointAreaBucket = pointAreaBuckets[i];
          var maxArea = d3Array.max(pointAreaBucket);
          var currentMaxIndex = pointAreaBucket.indexOf(maxArea);
          return thisBucket[currentMaxIndex];
        });

        // First and last data points are their own buckets.
        return [].concat([data[0]], subsampledData, [data[data.length - 1]]);
      };
      function calculateAreaOfPoints(data) {
        var xyData = data.map(function (point) {
          return [x(point), y(point)];
        });
        var pointAreas = d3Array.range(1, xyData.length - 1).map(function (i) {
          var lastPoint = xyData[i - 1];
          var thisPoint = xyData[i];
          var nextPoint = xyData[i + 1];
          return 0.5 * Math.abs((lastPoint[0] - nextPoint[0]) * (thisPoint[1] - lastPoint[1]) - (lastPoint[0] - thisPoint[0]) * (nextPoint[1] - lastPoint[1]));
        });
        return pointAreas;
      }
      rebind(largestTriangleOneBucket, dataBucketer, 'bucketSize');
      largestTriangleOneBucket.x = function (d) {
        if (!arguments.length) {
          return x;
        }
        x = d;
        return largestTriangleOneBucket;
      };
      largestTriangleOneBucket.y = function (d) {
        if (!arguments.length) {
          return y;
        }
        y = d;
        return largestTriangleOneBucket;
      };
      return largestTriangleOneBucket;
    }

    function largestTriangleThreeBucket () {
      var x = function x(d) {
        return d;
      };
      var y = function y(d) {
        return d;
      };
      var dataBucketer = bucket();
      var largestTriangleThreeBucket = function largestTriangleThreeBucket(data) {
        if (dataBucketer.bucketSize() >= data.length) {
          return data;
        }
        var buckets = dataBucketer(data.slice(1, data.length - 1));
        var firstBucket = data[0];
        var lastBucket = data[data.length - 1];

        // Keep track of the last selected bucket info and all buckets
        // (for the next bucket average)
        var allBuckets = [].concat([firstBucket], buckets, [lastBucket]);
        var lastSelectedX = x(firstBucket);
        var lastSelectedY = y(firstBucket);
        var subsampledData = buckets.map(function (thisBucket, i) {
          var nextAvgX = d3Array.mean(allBuckets[i + 1], x);
          var nextAvgY = d3Array.mean(allBuckets[i + 1], y);
          var xyData = thisBucket.map(function (item) {
            return [x(item), y(item)];
          });
          var areas = xyData.map(function (item) {
            return 0.5 * Math.abs((lastSelectedX - nextAvgX) * (item[1] - lastSelectedY) - (lastSelectedX - item[0]) * (nextAvgY - lastSelectedY));
          });
          var highestIndex = areas.indexOf(d3Array.max(areas));
          var highestXY = xyData[highestIndex];
          lastSelectedX = highestXY[0];
          lastSelectedY = highestXY[1];
          return thisBucket[highestIndex];
        });

        // First and last data points are their own buckets.
        return [].concat([data[0]], subsampledData, [data[data.length - 1]]);
      };
      rebind(largestTriangleThreeBucket, dataBucketer, 'bucketSize');
      largestTriangleThreeBucket.x = function (d) {
        if (!arguments.length) {
          return x;
        }
        x = d;
        return largestTriangleThreeBucket;
      };
      largestTriangleThreeBucket.y = function (d) {
        if (!arguments.length) {
          return y;
        }
        y = d;
        return largestTriangleThreeBucket;
      };
      return largestTriangleThreeBucket;
    }

    function modeMedian () {
      var dataBucketer = bucket();
      var value = function value(d) {
        return d;
      };
      var modeMedian = function modeMedian(data) {
        if (dataBucketer.bucketSize() > data.length) {
          return data;
        }
        var minMax = d3Array.extent(data, value);
        var buckets = dataBucketer(data.slice(1, data.length - 1));
        var subsampledData = buckets.map(function (thisBucket, i) {
          var frequencies = {};
          var mostFrequent;
          var mostFrequentIndex;
          var singleMostFrequent = true;
          var values = thisBucket.map(value);
          var globalMinMax = values.filter(function (value) {
            return value === minMax[0] || value === minMax[1];
          }).map(function (value) {
            return values.indexOf(value);
          })[0];
          if (globalMinMax !== undefined) {
            return thisBucket[globalMinMax];
          }
          values.forEach(function (item, i) {
            if (frequencies[item] === undefined) {
              frequencies[item] = 0;
            }
            frequencies[item]++;
            if (frequencies[item] > frequencies[mostFrequent] || mostFrequent === undefined) {
              mostFrequent = item;
              mostFrequentIndex = i;
              singleMostFrequent = true;
            } else if (frequencies[item] === frequencies[mostFrequent]) {
              singleMostFrequent = false;
            }
          });
          if (singleMostFrequent) {
            return thisBucket[mostFrequentIndex];
          } else {
            return thisBucket[Math.floor(thisBucket.length / 2)];
          }
        });

        // First and last data points are their own buckets.
        return [].concat([data[0]], subsampledData, [data[data.length - 1]]);
      };
      rebind(modeMedian, dataBucketer, 'bucketSize');
      modeMedian.value = function (x) {
        if (!arguments.length) {
          return value;
        }
        value = x;
        return modeMedian;
      };
      return modeMedian;
    }

    var functor$4 = (function (v) {
      return typeof v === 'function' ? v : function () {
        return v;
      };
    });

    // Renders an OHLC as an SVG path based on the given array of datapoints. Each
    // OHLC has a fixed width, whilst the x, open, high, low and close positions are
    // obtained from each point via the supplied accessor functions.
    var shapeOhlc = (function () {
      var context = null;
      var x = function x(d) {
        return d.date;
      };
      var open = function open(d) {
        return d.open;
      };
      var high = function high(d) {
        return d.high;
      };
      var low = function low(d) {
        return d.low;
      };
      var close = function close(d) {
        return d.close;
      };
      var orient = 'vertical';
      var width = functor$4(3);
      var ohlc = function ohlc(data) {
        var drawingContext = context || d3Path.path();
        data.forEach(function (d, i) {
          var xValue = x(d, i);
          var yOpen = open(d, i);
          var yHigh = high(d, i);
          var yLow = low(d, i);
          var yClose = close(d, i);
          var halfWidth = width(d, i) / 2;
          if (orient === 'vertical') {
            drawingContext.moveTo(xValue, yLow);
            drawingContext.lineTo(xValue, yHigh);
            drawingContext.moveTo(xValue, yOpen);
            drawingContext.lineTo(xValue - halfWidth, yOpen);
            drawingContext.moveTo(xValue, yClose);
            drawingContext.lineTo(xValue + halfWidth, yClose);
          } else {
            drawingContext.moveTo(yLow, xValue);
            drawingContext.lineTo(yHigh, xValue);
            drawingContext.moveTo(yOpen, xValue);
            drawingContext.lineTo(yOpen, xValue + halfWidth);
            drawingContext.moveTo(yClose, xValue);
            drawingContext.lineTo(yClose, xValue - halfWidth);
          }
        });
        return context ? null : drawingContext.toString();
      };
      ohlc.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return ohlc;
      };
      ohlc.x = function () {
        if (!arguments.length) {
          return x;
        }
        x = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.open = function () {
        if (!arguments.length) {
          return open;
        }
        open = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.high = function () {
        if (!arguments.length) {
          return high;
        }
        high = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.low = function () {
        if (!arguments.length) {
          return low;
        }
        low = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.close = function () {
        if (!arguments.length) {
          return close;
        }
        close = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.width = function () {
        if (!arguments.length) {
          return width;
        }
        width = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return ohlc;
      };
      ohlc.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return ohlc;
      };
      return ohlc;
    });

    // Renders a bar series as an SVG path based on the given array of datapoints. Each
    // bar has a fixed width, whilst the x, y and height are obtained from each data
    // point via the supplied accessor functions.
    var shapeBar = (function () {
      var context = null;
      var x = function x(d) {
        return d.x;
      };
      var y = function y(d) {
        return d.y;
      };
      var horizontalAlign = 'center';
      var verticalAlign = 'center';
      var height = function height(d) {
        return d.height;
      };
      var width = functor$4(3);
      var bar = function bar(data, index) {
        var drawingContext = context || d3Path.path();
        data.forEach(function (d, i) {
          var xValue = x.call(this, d, index || i);
          var yValue = y.call(this, d, index || i);
          var barHeight = height.call(this, d, index || i);
          var barWidth = width.call(this, d, index || i);
          var horizontalOffset;
          switch (horizontalAlign) {
            case 'left':
              horizontalOffset = barWidth;
              break;
            case 'right':
              horizontalOffset = 0;
              break;
            case 'center':
              horizontalOffset = barWidth / 2;
              break;
            default:
              throw new Error('Invalid horizontal alignment ' + horizontalAlign);
          }
          var verticalOffset;
          switch (verticalAlign) {
            case 'bottom':
              verticalOffset = -barHeight;
              break;
            case 'top':
              verticalOffset = 0;
              break;
            case 'center':
              verticalOffset = barHeight / 2;
              break;
            default:
              throw new Error('Invalid vertical alignment ' + verticalAlign);
          }
          drawingContext.rect(xValue - horizontalOffset, yValue - verticalOffset, barWidth, barHeight);
        }, this);
        return context ? null : drawingContext.toString();
      };
      bar.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return bar;
      };
      bar.x = function () {
        if (!arguments.length) {
          return x;
        }
        x = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return bar;
      };
      bar.y = function () {
        if (!arguments.length) {
          return y;
        }
        y = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return bar;
      };
      bar.width = function () {
        if (!arguments.length) {
          return width;
        }
        width = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return bar;
      };
      bar.horizontalAlign = function () {
        if (!arguments.length) {
          return horizontalAlign;
        }
        horizontalAlign = arguments.length <= 0 ? undefined : arguments[0];
        return bar;
      };
      bar.height = function () {
        if (!arguments.length) {
          return height;
        }
        height = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return bar;
      };
      bar.verticalAlign = function () {
        if (!arguments.length) {
          return verticalAlign;
        }
        verticalAlign = arguments.length <= 0 ? undefined : arguments[0];
        return bar;
      };
      return bar;
    });

    // Renders a candlestick as an SVG path based on the given array of datapoints. Each
    // candlestick has a fixed width, whilst the x, open, high, low and close positions are
    // obtained from each point via the supplied accessor functions.
    var shapeCandlestick = (function () {
      var context = null;
      var x = function x(d) {
        return d.date;
      };
      var open = function open(d) {
        return d.open;
      };
      var high = function high(d) {
        return d.high;
      };
      var low = function low(d) {
        return d.low;
      };
      var close = function close(d) {
        return d.close;
      };
      var width = functor$4(3);
      var candlestick = function candlestick(data) {
        var drawingContext = context || d3Path.path();
        data.forEach(function (d, i) {
          var xValue = x(d, i);
          var yOpen = open(d, i);
          var yHigh = high(d, i);
          var yLow = low(d, i);
          var yClose = close(d, i);
          var barWidth = width(d, i);
          var halfBarWidth = barWidth / 2;

          // Body
          drawingContext.rect(xValue - halfBarWidth, yOpen, barWidth, yClose - yOpen);
          // High wick
          // // Move to the max price of close or open; draw the high wick
          // N.B. Math.min() is used as we're dealing with pixel values,
          // the lower the pixel value, the higher the price!
          drawingContext.moveTo(xValue, Math.min(yClose, yOpen));
          drawingContext.lineTo(xValue, yHigh);
          // Low wick
          // // Move to the min price of close or open; draw the low wick
          // N.B. Math.max() is used as we're dealing with pixel values,
          // the higher the pixel value, the lower the price!
          drawingContext.moveTo(xValue, Math.max(yClose, yOpen));
          drawingContext.lineTo(xValue, yLow);
        });
        return context ? null : drawingContext.toString();
      };
      candlestick.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return candlestick;
      };
      candlestick.x = function () {
        if (!arguments.length) {
          return x;
        }
        x = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      candlestick.open = function () {
        if (!arguments.length) {
          return open;
        }
        open = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      candlestick.high = function () {
        if (!arguments.length) {
          return high;
        }
        high = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      candlestick.low = function () {
        if (!arguments.length) {
          return low;
        }
        low = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      candlestick.close = function () {
        if (!arguments.length) {
          return close;
        }
        close = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      candlestick.width = function () {
        if (!arguments.length) {
          return width;
        }
        width = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return candlestick;
      };
      return candlestick;
    });

    // Renders a box plot series as an SVG path based on the given array of datapoints.
    var shapeBoxPlot = (function () {
      var context = null;
      var value = function value(d) {
        return d.value;
      };
      var median = function median(d) {
        return d.median;
      };
      var upperQuartile = function upperQuartile(d) {
        return d.upperQuartile;
      };
      var lowerQuartile = function lowerQuartile(d) {
        return d.lowerQuartile;
      };
      var high = function high(d) {
        return d.high;
      };
      var low = function low(d) {
        return d.low;
      };
      var orient = 'vertical';
      var width = functor$4(5);
      var cap = functor$4(0.5);
      var boxPlot = function boxPlot(data) {
        var drawingContext = context || d3Path.path();
        data.forEach(function (d, i) {
          // naming convention is for vertical orientation
          var _value = value(d, i);
          var _width = width(d, i);
          var halfWidth = _width / 2;
          var capWidth = _width * cap(d, i);
          var halfCapWidth = capWidth / 2;
          var _high = high(d, i);
          var _upperQuartile = upperQuartile(d, i);
          var _median = median(d, i);
          var _lowerQuartile = lowerQuartile(d, i);
          var _low = low(d, i);
          var upperQuartileToLowerQuartile = _lowerQuartile - _upperQuartile;
          if (orient === 'vertical') {
            // Upper whisker
            drawingContext.moveTo(_value - halfCapWidth, _high);
            drawingContext.lineTo(_value + halfCapWidth, _high);
            drawingContext.moveTo(_value, _high);
            drawingContext.lineTo(_value, _upperQuartile);

            // Box
            drawingContext.rect(_value - halfWidth, _upperQuartile, _width, upperQuartileToLowerQuartile);
            drawingContext.moveTo(_value - halfWidth, _median);
            // Median line
            drawingContext.lineTo(_value + halfWidth, _median);

            // Lower whisker
            drawingContext.moveTo(_value, _lowerQuartile);
            drawingContext.lineTo(_value, _low);
            drawingContext.moveTo(_value - halfCapWidth, _low);
            drawingContext.lineTo(_value + halfCapWidth, _low);
          } else {
            // Lower whisker
            drawingContext.moveTo(_low, _value - halfCapWidth);
            drawingContext.lineTo(_low, _value + halfCapWidth);
            drawingContext.moveTo(_low, _value);
            drawingContext.lineTo(_lowerQuartile, _value);

            // Box
            drawingContext.rect(_lowerQuartile, _value - halfWidth, -upperQuartileToLowerQuartile, _width);
            drawingContext.moveTo(_median, _value - halfWidth);
            drawingContext.lineTo(_median, _value + halfWidth);

            // Upper whisker
            drawingContext.moveTo(_upperQuartile, _value);
            drawingContext.lineTo(_high, _value);
            drawingContext.moveTo(_high, _value - halfCapWidth);
            drawingContext.lineTo(_high, _value + halfCapWidth);
          }
        });
        return context ? null : drawingContext.toString();
      };
      boxPlot.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return boxPlot;
      };
      boxPlot.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.median = function () {
        if (!arguments.length) {
          return median;
        }
        median = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.upperQuartile = function () {
        if (!arguments.length) {
          return upperQuartile;
        }
        upperQuartile = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.lowerQuartile = function () {
        if (!arguments.length) {
          return lowerQuartile;
        }
        lowerQuartile = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.high = function () {
        if (!arguments.length) {
          return high;
        }
        high = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.low = function () {
        if (!arguments.length) {
          return low;
        }
        low = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.width = function () {
        if (!arguments.length) {
          return width;
        }
        width = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return boxPlot;
      };
      boxPlot.cap = function () {
        if (!arguments.length) {
          return cap;
        }
        cap = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      return boxPlot;
    });

    // Renders an error bar series as an SVG path based on the given array of datapoints.
    var shapeErrorBar = (function () {
      var context = null;
      var value = function value(d) {
        return d.x;
      };
      var high = function high(d) {
        return d.high;
      };
      var low = function low(d) {
        return d.low;
      };
      var orient = 'vertical';
      var width = functor$4(5);
      var errorBar = function errorBar(data) {
        var drawingContext = context || d3Path.path();
        data.forEach(function (d, i) {
          // naming convention is for vertical orientation
          var _value = value(d, i);
          var _width = width(d, i);
          var halfWidth = _width / 2;
          var _high = high(d, i);
          var _low = low(d, i);
          if (orient === 'vertical') {
            drawingContext.moveTo(_value - halfWidth, _high);
            drawingContext.lineTo(_value + halfWidth, _high);
            drawingContext.moveTo(_value, _high);
            drawingContext.lineTo(_value, _low);
            drawingContext.moveTo(_value - halfWidth, _low);
            drawingContext.lineTo(_value + halfWidth, _low);
          } else {
            drawingContext.moveTo(_low, _value - halfWidth);
            drawingContext.lineTo(_low, _value + halfWidth);
            drawingContext.moveTo(_low, _value);
            drawingContext.lineTo(_high, _value);
            drawingContext.moveTo(_high, _value - halfWidth);
            drawingContext.lineTo(_high, _value + halfWidth);
          }
        });
        return context ? null : drawingContext.toString();
      };
      errorBar.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return errorBar;
      };
      errorBar.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return errorBar;
      };
      errorBar.high = function () {
        if (!arguments.length) {
          return high;
        }
        high = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return errorBar;
      };
      errorBar.low = function () {
        if (!arguments.length) {
          return low;
        }
        low = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return errorBar;
      };
      errorBar.width = function () {
        if (!arguments.length) {
          return width;
        }
        width = functor$4(arguments.length <= 0 ? undefined : arguments[0]);
        return errorBar;
      };
      errorBar.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return errorBar;
      };
      return errorBar;
    });

    var functor$3 = (function (d) {
      return typeof d === 'function' ? d : function () {
        return d;
      };
    });

    // "Caution: avoid interpolating to or from the number zero when the interpolator is used to generate
    // a string (such as with attr).
    // Very small values, when stringified, may be converted to scientific notation and
    // cause a temporarily invalid attribute or style property value.
    // For example, the number 0.0000001 is converted to the string "1e-7".
    // This is particularly noticeable when interpolating opacity values.
    // To avoid scientific notation, start or end the transition at 1e-6,
    // which is the smallest value that is not stringified in exponential notation."
    // - https://github.com/mbostock/d3/wiki/Transitions#d3_interpolateNumber
    var effectivelyZero = 1e-6;
    var isTransition = function isTransition(selectionOrTransition) {
      return selectionOrTransition.selection() !== selectionOrTransition;
    };

    // Wrapper around d3's selectAll/data data-join, which allows decoration of the result.
    // This is achieved by appending the element to the enter selection before exposing it.
    // A default transition of fade in/out is also implicitly added but can be modified.
    var dataJoin = (function (element, className) {
      element = element || 'g';
      var key = function key(_, i) {
        return i;
      };
      var explicitTransition = null;
      var dataJoin = function dataJoin(container, data) {
        data = data || function (d) {
          return d;
        };
        var selection = container.selection();
        var implicitTransition = isTransition(container) ? container : null;
        var selected = selection.selectChildren(className == null ? element : "".concat(element, ".").concat(className));
        var update = selected.data(data, key);
        var enter = update.enter().append(element).attr('class', className);
        var exit = update.exit();

        // automatically merge in the enter selection
        update = update.merge(enter);

        // if transitions are enabled apply a default fade in/out transition
        var transition = implicitTransition || explicitTransition;
        if (transition) {
          update = update.transition(transition).style('opacity', 1);
          enter.style('opacity', effectivelyZero);
          exit = exit.transition(transition).style('opacity', effectivelyZero);
        }
        exit.remove();
        update.enter = function () {
          return enter;
        };
        update.exit = function () {
          return exit;
        };
        return update;
      };
      dataJoin.element = function () {
        if (!arguments.length) {
          return element;
        }
        element = arguments.length <= 0 ? undefined : arguments[0];
        return dataJoin;
      };
      dataJoin.className = function () {
        if (!arguments.length) {
          return className;
        }
        className = arguments.length <= 0 ? undefined : arguments[0];
        return dataJoin;
      };
      dataJoin.key = function () {
        if (!arguments.length) {
          return key;
        }
        key = arguments.length <= 0 ? undefined : arguments[0];
        return dataJoin;
      };
      dataJoin.transition = function () {
        if (!arguments.length) {
          return explicitTransition;
        }
        explicitTransition = arguments.length <= 0 ? undefined : arguments[0];
        return dataJoin;
      };
      return dataJoin;
    });

    var label = (function (layoutStrategy) {
      var decorate = function decorate() {};
      var size = function size() {
        return [0, 0];
      };
      var position = function position(d, i) {
        return [d.x, d.y];
      };
      var strategy = layoutStrategy || function (x) {
        return x;
      };
      var component = function component() {};
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var dataJoin$1 = dataJoin('g', 'label');
      var label = function label(selection) {
        selection.each(function (data, index, group) {
          var g = dataJoin$1(d3Selection.select(group[index]), data).call(component);

          // obtain the rectangular bounding boxes for each child
          var nodes = g.nodes();
          var childRects = nodes.map(function (node, i) {
            var d = d3Selection.select(node).datum();
            var pos = position(d, i, nodes);
            var childPos = [xScale(pos[0]), yScale(pos[1])];
            var childSize = size(d, i, nodes);
            return {
              hidden: false,
              x: childPos[0],
              y: childPos[1],
              width: childSize[0],
              height: childSize[1]
            };
          });

          // apply the strategy to derive the layout. The strategy does not change the order
          // or number of label.
          var layout = strategy(childRects);
          g.attr('style', function (_, i) {
            return 'display:' + (layout[i].hidden ? 'none' : 'inherit');
          }).attr('transform', function (_, i) {
            return 'translate(' + layout[i].x + ', ' + layout[i].y + ')';
          })
          // set the layout width / height so that children can use SVG layout if required
          .attr('layout-width', function (_, i) {
            return layout[i].width;
          }).attr('layout-height', function (_, i) {
            return layout[i].height;
          }).attr('anchor-x', function (d, i, g) {
            return childRects[i].x - layout[i].x;
          }).attr('anchor-y', function (d, i, g) {
            return childRects[i].y - layout[i].y;
          });
          g.call(component);
          decorate(g, data, index);
        });
      };
      rebindAll(label, dataJoin$1, include('key'));
      rebindAll(label, strategy);
      label.size = function () {
        if (!arguments.length) {
          return size;
        }
        size = functor$3(arguments.length <= 0 ? undefined : arguments[0]);
        return label;
      };
      label.position = function () {
        if (!arguments.length) {
          return position;
        }
        position = functor$3(arguments.length <= 0 ? undefined : arguments[0]);
        return label;
      };
      label.component = function () {
        if (!arguments.length) {
          return component;
        }
        component = arguments.length <= 0 ? undefined : arguments[0];
        return label;
      };
      label.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return label;
      };
      label.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return label;
      };
      label.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return label;
      };
      return label;
    });

    var textLabel = (function (layoutStrategy) {
      var padding = 2;
      var value = function value(x) {
        return x;
      };
      var textJoin = dataJoin('text');
      var rectJoin = dataJoin('rect');
      var pointJoin = dataJoin('circle');
      var textLabel = function textLabel(selection) {
        selection.each(function (data, index, group) {
          var node = group[index];
          var nodeSelection = d3Selection.select(node);
          var width = Number(node.getAttribute('layout-width'));
          var height = Number(node.getAttribute('layout-height'));
          var rect = rectJoin(nodeSelection, [data]);
          rect.attr('width', width).attr('height', height);
          var anchorX = Number(node.getAttribute('anchor-x'));
          var anchorY = Number(node.getAttribute('anchor-y'));
          var circle = pointJoin(nodeSelection, [data]);
          circle.attr('r', 2).attr('cx', anchorX).attr('cy', anchorY);
          var text = textJoin(nodeSelection, [data]);
          text.enter().attr('dy', '0.9em').attr('transform', "translate(".concat(padding, ", ").concat(padding, ")"));
          text.text(value);
        });
      };
      textLabel.padding = function () {
        if (!arguments.length) {
          return padding;
        }
        padding = arguments.length <= 0 ? undefined : arguments[0];
        return textLabel;
      };
      textLabel.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = functor$3(arguments.length <= 0 ? undefined : arguments[0]);
        return textLabel;
      };
      return textLabel;
    });

    var isIntersecting = function isIntersecting(a, b) {
      return !(a.x >= b.x + b.width || a.x + a.width <= b.x || a.y >= b.y + b.height || a.y + a.height <= b.y);
    };
    var intersect = (function (a, b) {
      if (isIntersecting(a, b)) {
        var left = Math.max(a.x, b.x);
        var right = Math.min(a.x + a.width, b.x + b.width);
        var top = Math.max(a.y, b.y);
        var bottom = Math.min(a.y + a.height, b.y + b.height);
        return (right - left) * (bottom - top);
      } else {
        return 0;
      }
    });

    // computes the area of overlap between the rectangle with the given index with the
    // rectangles in the array
    var collisionArea = function collisionArea(rectangles, index) {
      return d3Array.sum(rectangles.map(function (d, i) {
        return index === i ? 0 : intersect(rectangles[index], d);
      }));
    };

    var getPlacement = function getPlacement(x, y, width, height, location) {
      return {
        x: x,
        y: y,
        width: width,
        height: height,
        location: location
      };
    };

    // returns all the potential placements of the given label
    var placements = (function (label) {
      var x = label.x;
      var y = label.y;
      var width = label.width;
      var height = label.height;
      return [getPlacement(x, y, width, height, 'bottom-right'), getPlacement(x - width, y, width, height, 'bottom-left'), getPlacement(x - width, y - height, width, height, 'top-left'), getPlacement(x, y - height, width, height, 'top-right'), getPlacement(x, y - height / 2, width, height, 'middle-right'), getPlacement(x - width / 2, y, width, height, 'bottom-center'), getPlacement(x - width, y - height / 2, width, height, 'middle-left'), getPlacement(x - width / 2, y - height, width, height, 'top-center')];
    });

    var substitute = function substitute(array, index, substitution) {
      return [].concat(_toConsumableArray(array.slice(0, index)), [substitution], _toConsumableArray(array.slice(index + 1)));
    };
    var lessThan = function lessThan(a, b) {
      return a < b;
    };

    // a layout takes an array of rectangles and allows their locations to be optimised.
    // it is constructed using two functions, locationScore, which score the placement of and
    // individual rectangle, and winningScore which takes the scores for a rectangle
    // at two different locations and assigns a winningScore.
    var layoutComponent = function layoutComponent() {
      var score = null;
      var winningScore = lessThan;
      var locationScore = function locationScore() {
        return 0;
      };
      var rectangles;
      var evaluatePlacement = function evaluatePlacement(placement, index) {
        return score - locationScore(rectangles[index], index, rectangles) + locationScore(placement, index, substitute(rectangles, index, placement));
      };
      var layout = function layout(placement, index) {
        if (!score) {
          score = d3Array.sum(rectangles.map(function (r, i) {
            return locationScore(r, i, rectangles);
          }));
        }
        var newScore = evaluatePlacement(placement, index);
        if (winningScore(newScore, score)) {
          return layoutComponent().locationScore(locationScore).winningScore(winningScore).score(newScore).rectangles(substitute(rectangles, index, placement));
        } else {
          return layout;
        }
      };
      layout.rectangles = function () {
        if (!arguments.length) {
          return rectangles;
        }
        rectangles = arguments.length <= 0 ? undefined : arguments[0];
        return layout;
      };
      layout.score = function () {
        if (!arguments.length) {
          return score;
        }
        score = arguments.length <= 0 ? undefined : arguments[0];
        return layout;
      };
      layout.winningScore = function () {
        if (!arguments.length) {
          return winningScore;
        }
        winningScore = arguments.length <= 0 ? undefined : arguments[0];
        return layout;
      };
      layout.locationScore = function () {
        if (!arguments.length) {
          return locationScore;
        }
        locationScore = arguments.length <= 0 ? undefined : arguments[0];
        return layout;
      };
      return layout;
    };

    var greedy = (function () {
      var bounds;
      var containerPenalty = function containerPenalty(rectangle) {
        return bounds ? rectangle.width * rectangle.height - intersect(rectangle, bounds) : 0;
      };
      var penaltyForRectangle = function penaltyForRectangle(rectangle, index, rectangles) {
        return collisionArea(rectangles, index) + containerPenalty(rectangle);
      };
      var strategy = function strategy(data) {
        var rectangles = layoutComponent().locationScore(penaltyForRectangle).rectangles(data);
        data.forEach(function (rectangle, index) {
          placements(rectangle).forEach(function (placement, placementIndex) {
            rectangles = rectangles(placement, index);
          });
        });
        return rectangles.rectangles();
      };
      strategy.bounds = function () {
        if (!arguments.length) {
          return bounds;
        }
        bounds = arguments.length <= 0 ? undefined : arguments[0];
        return strategy;
      };
      return strategy;
    });

    var randomItem = function randomItem(array) {
      return array[randomIndex(array)];
    };
    var randomIndex = function randomIndex(array) {
      return Math.floor(Math.random() * array.length);
    };
    var annealing = (function () {
      var temperature = 1000;
      var cooling = 1;
      var bounds;
      var orientationPenalty = function orientationPenalty(rectangle) {
        switch (rectangle.location) {
          case 'bottom-right':
            return 0;
          case 'middle-right':
          case 'bottom-center':
            return rectangle.width * rectangle.height / 8;
        }
        return rectangle.width * rectangle.height / 4;
      };
      var containerPenalty = function containerPenalty(rectangle) {
        return bounds ? rectangle.width * rectangle.height - intersect(rectangle, bounds) : 0;
      };
      var penaltyForRectangle = function penaltyForRectangle(rectangle, index, rectangles) {
        return collisionArea(rectangles, index) + containerPenalty(rectangle) + orientationPenalty(rectangle);
      };
      var strategy = function strategy(data) {
        var currentTemperature = temperature;

        // use annealing to allow a new score to be picked even if it is worse than the old
        var winningScore = function winningScore(newScore, oldScore) {
          return Math.exp((oldScore - newScore) / currentTemperature) > Math.random();
        };
        var rectangles = layoutComponent().locationScore(penaltyForRectangle).winningScore(winningScore).rectangles(data);
        while (currentTemperature > 0) {
          var index = randomIndex(data);
          var randomNewPlacement = randomItem(placements(data[index]));
          rectangles = rectangles(randomNewPlacement, index);
          currentTemperature -= cooling;
        }
        return rectangles.rectangles();
      };
      strategy.temperature = function () {
        if (!arguments.length) {
          return temperature;
        }
        temperature = arguments.length <= 0 ? undefined : arguments[0];
        return strategy;
      };
      strategy.cooling = function () {
        if (!arguments.length) {
          return cooling;
        }
        cooling = arguments.length <= 0 ? undefined : arguments[0];
        return strategy;
      };
      strategy.bounds = function () {
        if (!arguments.length) {
          return bounds;
        }
        bounds = arguments.length <= 0 ? undefined : arguments[0];
        return strategy;
      };
      return strategy;
    });

    var scanForObject = function scanForObject(array, comparator) {
      return array[d3Array.scan(array, comparator)];
    };
    var removeOverlaps = (function (adaptedStrategy) {
      adaptedStrategy = adaptedStrategy || function (x) {
        return x;
      };
      var removeOverlaps = function removeOverlaps(layout) {
        layout = adaptedStrategy(layout);
        // eslint-disable-next-line no-constant-condition
        var _loop = function _loop() {
          // find the collision area for all overlapping rectangles, hiding the one
          // with the greatest overlap
          var visible = layout.filter(function (d) {
            return !d.hidden;
          });
          var collisions = visible.map(function (d, i) {
            return [d, collisionArea(visible, i)];
          });
          var maximumCollision = scanForObject(collisions, function (a, b) {
            return b[1] - a[1];
          });
          if (maximumCollision[1] > 0) {
            maximumCollision[0].hidden = true;
          } else {
            return "break";
          }
        };
        while (true) {
          var _ret = _loop();
          if (_ret === "break") break;
        }
        return layout;
      };
      rebindAll(removeOverlaps, adaptedStrategy);
      return removeOverlaps;
    });

    var boundingBox = (function () {
      var bounds = [0, 0];
      var strategy = function strategy(data) {
        return data.map(function (d, i) {
          var tx = d.x;
          var ty = d.y;
          if (tx + d.width > bounds[0]) {
            tx -= d.width;
          }
          if (ty + d.height > bounds[1]) {
            ty -= d.height;
          }
          return {
            height: d.height,
            width: d.width,
            x: tx,
            y: ty
          };
        });
      };
      strategy.bounds = function () {
        if (!arguments.length) {
          return bounds;
        }
        bounds = arguments.length <= 0 ? undefined : arguments[0];
        return strategy;
      };
      return strategy;
    });

    var functor$2 = (function (d) {
      return typeof d === 'function' ? d : function () {
        return d;
      };
    });

    // Checks that passed properties are 'defined', meaning that calling them with (d, i) returns non null values
    function defined() {
      var outerArguments = arguments;
      return function (d, i) {
        for (var c = 0, j = outerArguments.length; c < j; c++) {
          if (outerArguments[c](d, i) == null) {
            return false;
          }
        }
        return true;
      };
    }

    // determines the offset required along the cross scale based
    // on the series alignment
    var alignOffset = (function (align, width) {
      switch (align) {
        case 'left':
          return width / 2;
        case 'right':
          return -width / 2;
        default:
          return 0;
      }
    });

    var createBase = (function (initialValues) {
      var env = Object.assign({}, initialValues);
      var base = function base() {};
      Object.keys(env).forEach(function (key) {
        base[key] = function () {
          if (!arguments.length) {
            return env[key];
          }
          env[key] = arguments.length <= 0 ? undefined : arguments[0];
          return base;
        };
      });
      return base;
    });

    var xyBase = (function () {
      var baseValue = function baseValue() {
        return 0;
      };
      var crossValue = function crossValue(d) {
        return d.x;
      };
      var mainValue = function mainValue(d) {
        return d.y;
      };
      var align = 'center';
      var bandwidth = function bandwidth() {
        return 5;
      };
      var orient = 'vertical';
      var base = createBase({
        decorate: function decorate() {},
        defined: function defined$1(d, i) {
          return defined(baseValue, crossValue, mainValue)(d, i);
        },
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      base.values = function (d, i) {
        var width = bandwidth(d, i);
        var offset = alignOffset(align, width);
        var xScale = base.xScale();
        var yScale = base.yScale();
        if (orient === 'vertical') {
          var y = yScale(mainValue(d, i), i);
          var y0 = yScale(baseValue(d, i), i);
          var x = xScale(crossValue(d, i), i) + offset;
          return {
            d: d,
            x: x,
            y: y,
            y0: y0,
            width: width,
            height: y - y0,
            origin: [x, y],
            baseOrigin: [x, y0],
            transposedX: x,
            transposedY: y
          };
        } else {
          var _y = xScale(mainValue(d, i), i);
          var _y2 = xScale(baseValue(d, i), i);
          var _x = yScale(crossValue(d, i), i) + offset;
          return {
            d: d,
            x: _x,
            y: _y,
            y0: _y2,
            width: width,
            height: _y - _y2,
            origin: [_y, _x],
            baseOrigin: [_y2, _x],
            transposedX: _y,
            transposedY: _x
          };
        }
      };
      base.xValues = function () {
        return orient === 'vertical' ? [crossValue] : [baseValue, mainValue];
      };
      base.yValues = function () {
        return orient !== 'vertical' ? [crossValue] : [baseValue, mainValue];
      };
      base.baseValue = function () {
        if (!arguments.length) {
          return baseValue;
        }
        baseValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.crossValue = function () {
        if (!arguments.length) {
          return crossValue;
        }
        crossValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.mainValue = function () {
        if (!arguments.length) {
          return mainValue;
        }
        mainValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.bandwidth = function () {
        if (!arguments.length) {
          return bandwidth;
        }
        bandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.align = function () {
        if (!arguments.length) {
          return align;
        }
        align = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var red = '#c60';
    var green = '#6c0';
    var black = '#000';
    var gray = '#ddd';
    var darkGray = '#999';
    var colors = {
      red: red,
      green: green,
      black: black,
      gray: gray,
      darkGray: darkGray
    };

    var seriesSvgLine = (function () {
      var base = xyBase();
      var lineData = d3Shape.line().x(function (d, i) {
        return base.values(d, i).transposedX;
      }).y(function (d, i) {
        return base.values(d, i).transposedY;
      });
      var join = dataJoin('path', 'line');
      var line = function line(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        lineData.defined(base.defined());
        selection.each(function (data, index, group) {
          var path = join(d3Selection.select(group[index]), [data]);
          path.enter().attr('fill', 'none').attr('stroke', colors.black);
          path.attr('d', lineData);
          base.decorate()(path, data, index);
        });
      };
      rebindAll(line, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(line, join, 'key');
      rebind(line, lineData, 'curve');
      return line;
    });

    var seriesCanvasLine = (function () {
      var base = xyBase();
      var lineData = d3Shape.line().x(function (d, i) {
        return base.values(d, i).transposedX;
      }).y(function (d, i) {
        return base.values(d, i).transposedY;
      });
      var line = function line(data) {
        var context = lineData.context();
        context.beginPath();
        context.strokeStyle = colors.black;
        context.fillStyle = 'transparent';
        base.decorate()(context, data);
        lineData.defined(base.defined())(data);
        context.fill();
        context.stroke();
        context.closePath();
      };
      rebindAll(line, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(line, lineData, 'curve', 'context');
      return line;
    });

    var baseScale = (function () {
      var domain = [0, 1];
      var range = [-1, 1];
      var base = function base() {};
      base.domain = function () {
        if (!arguments.length) {
          return domain;
        }
        domain = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.range = function () {
        if (!arguments.length) {
          return range;
        }
        range = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var bufferBuilder = (function () {
      var attributes = {};
      var uniforms = {};
      var elementIndices = null;
      var bufferBuilder = function bufferBuilder(programBuilder, program) {
        var gl = programBuilder.context();
        Object.keys(attributes).forEach(function (name) {
          var attribute = attributes[name];
          if (typeof attribute !== 'function') {
            throw new Error("Expected an attribute for ".concat(name, ", found ").concat(attribute));
          }
          var location = gl.getAttribLocation(program, name);
          attribute.location(location)(programBuilder);
        });
        Object.keys(uniforms).forEach(function (name) {
          var uniform = uniforms[name];
          if (typeof uniform !== 'function') {
            throw new Error("Expected a uniform for ".concat(name, ", found ").concat(uniform));
          }
          var location = gl.getUniformLocation(program, name);
          uniform.location(location)(programBuilder);
        });
        if (elementIndices !== null) {
          elementIndices(programBuilder);
        }
      };
      bufferBuilder.flush = function () {
        Object.values(attributes).forEach(function (attribute) {
          return attribute.clear();
        });
        Object.values(uniforms).forEach(function (uniform) {
          return uniform.clear();
        });
        if (elementIndices !== null) elementIndices.clear();
      };
      bufferBuilder.attribute = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        if (args.length === 1) {
          return attributes[args[0]];
        }
        attributes[args[0]] = args[1];
        return bufferBuilder;
      };
      bufferBuilder.uniform = function () {
        for (var _len2 = arguments.length, args = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
          args[_key2] = arguments[_key2];
        }
        if (args.length === 1) {
          return uniforms[args[0]];
        }
        uniforms[args[0]] = args[1];
        return bufferBuilder;
      };
      bufferBuilder.elementIndices = function () {
        if (!arguments.length) {
          return elementIndices;
        }
        elementIndices = arguments.length <= 0 ? undefined : arguments[0];
        return bufferBuilder;
      };
      return bufferBuilder;
    });

    var uniform = (function (initialData) {
      var location = -1;
      var data = initialData;
      var dirty = true;
      var build = function build(programBuilder) {
        if (!dirty) {
          return;
        }
        var gl = programBuilder.context();
        if (Array.isArray(data)) {
          switch (data.length) {
            case 1:
              gl.uniform1fv(location, data);
              break;
            case 2:
              gl.uniform2fv(location, data);
              break;
            case 3:
              gl.uniform3fv(location, data);
              break;
            case 4:
              gl.uniform4fv(location, data);
              break;
            default:
              throw new Error("Uniform supports up to 4 elements. ".concat(data.length, " provided."));
          }
        } else {
          gl.uniform1f(location, data);
        }
        dirty = false;
      };
      build.clear = function () {
        dirty = true;
      };
      build.location = function () {
        if (!arguments.length) {
          return location;
        }
        if (location !== (arguments.length <= 0 ? undefined : arguments[0])) {
          location = arguments.length <= 0 ? undefined : arguments[0];
          dirty = true;
        }
        return build;
      };
      build.data = function () {
        if (!arguments.length) {
          return data;
        }
        data = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return build;
      };
      return build;
    });

    var drawModes = {
      POINTS: 0,
      LINES: 1,
      LINE_LOOP: 2,
      LINE_STRIP: 3,
      TRIANGLES: 4,
      TRIANGLE_STRIP: 5,
      TRIANGLE_FAN: 6
    };

    var programBuilder = (function () {
      var context = null;
      var program = null;
      var vertexShader = null;
      var fragmentShader = null;
      var programVertexShader = null;
      var programFragmentShader = null;
      var mode = drawModes.TRIANGLES;
      var subInstanceCount = 0;
      var buffers = bufferBuilder();
      var debug = false;
      var extInstancedArrays = null;
      var dirty = true;
      var pixelRatio = 1;
      var build = function build(count) {
        if (context == null) {
          return;
        }
        var vertexShaderSource = vertexShader();
        var fragmentShaderSource = fragmentShader();
        if (newProgram(program, vertexShaderSource, fragmentShaderSource)) {
          program = createProgram(vertexShaderSource, fragmentShaderSource);
          programVertexShader = vertexShaderSource;
          programFragmentShader = fragmentShaderSource;
          dirty = false;
        }
        context.useProgram(program);
        buffers.uniform('uScreen', uniform([context.canvas.width / pixelRatio, context.canvas.height / pixelRatio]));
        buffers(build, program);
        if (subInstanceCount === 0) {
          if (buffers.elementIndices() == null) {
            context.drawArrays(mode, 0, count);
          } else {
            context.drawElements(mode, count, context.UNSIGNED_SHORT, 0);
          }
        } else {
          if (buffers.elementIndices() == null) {
            extInstancedArrays.drawArraysInstancedANGLE(mode, 0, subInstanceCount, count);
          } else {
            var elementIndicesLength = buffers.elementIndices().data().length;
            if (subInstanceCount !== elementIndicesLength) {
              throw new Error("Expected elementIndices length ".concat(elementIndicesLength) + " to match subInstanceCount ".concat(subInstanceCount, "."));
            }
            extInstancedArrays.drawElementsInstancedANGLE(mode, subInstanceCount, context.UNSIGNED_SHORT, 0, count);
          }
        }
      };
      build.extInstancedArrays = function () {
        return extInstancedArrays;
      };
      build.context = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        if (!args.length) {
          return context;
        }
        if (args[0] == null || args[0] !== context) {
          buffers.flush();
          dirty = true;
        }
        if (args[0] != null && args[0] !== context) {
          extInstancedArrays = args[0].getExtension('ANGLE_instanced_arrays');
        }
        context = args[0];
        return build;
      };
      build.buffers = function () {
        if (!arguments.length) {
          return buffers;
        }
        buffers = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.vertexShader = function () {
        if (!arguments.length) {
          return vertexShader;
        }
        vertexShader = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.fragmentShader = function () {
        if (!arguments.length) {
          return fragmentShader;
        }
        fragmentShader = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.mode = function () {
        if (!arguments.length) {
          return mode;
        }
        mode = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.subInstanceCount = function () {
        if (!arguments.length) {
          return subInstanceCount;
        }
        subInstanceCount = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.debug = function () {
        if (!arguments.length) {
          return debug;
        }
        debug = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      build.pixelRatio = function () {
        if (!arguments.length) {
          return pixelRatio;
        }
        pixelRatio = arguments.length <= 0 ? undefined : arguments[0];
        return build;
      };
      return build;
      function newProgram(program, vertexShader, fragmentShader) {
        if (!program || dirty) {
          return true;
        }
        return vertexShader !== programVertexShader || fragmentShader !== programFragmentShader;
      }
      function createProgram(vertexShaderSource, fragmentShaderSource) {
        var vertexShader = loadShader(vertexShaderSource, context.VERTEX_SHADER);
        var fragmentShader = loadShader(fragmentShaderSource, context.FRAGMENT_SHADER);
        var program = context.createProgram();
        context.attachShader(program, vertexShader);
        context.attachShader(program, fragmentShader);
        context.linkProgram(program);
        if (debug && !context.getProgramParameter(program, context.LINK_STATUS)) {
          var message = context.getProgramInfoLog(program);
          context.deleteProgram(program);
          throw new Error("Failed to link program : ".concat(message, "\n            Vertex Shader : ").concat(vertexShaderSource, "\n            Fragment Shader : ").concat(fragmentShaderSource));
        }
        return program;
      }
      function loadShader(source, type) {
        var shader = context.createShader(type);
        context.shaderSource(shader, source);
        context.compileShader(shader);
        if (debug && !context.getShaderParameter(shader, context.COMPILE_STATUS)) {
          var message = context.getShaderInfoLog(shader);
          context.deleteShader(shader);
          throw new Error("Failed to compile shader : ".concat(message, "\n            Shader : ").concat(source));
        }
        return shader;
      }
    });

    var shaderBuilder = (function (base) {
      var shaderHeaders = [];
      var shaderBodies = [];
      var build = function build() {
        return base(shaderHeaders.join('\n'), shaderBodies.join('\n'));
      };
      function append(array, element) {
        array.push(element);
      }
      function insert(array, element, before) {
        var beforeIndex = array.indexOf(before);
        array.splice(beforeIndex >= 0 ? beforeIndex : array.length, 0, element);
      }
      function appendIfNotExists(array, element) {
        var elementIndex = array.indexOf(element);
        if (elementIndex === -1) {
          array.push(element);
        }
      }
      build.appendHeader = function (header) {
        append(shaderHeaders, header);
        return build;
      };
      build.insertHeader = function (header, before) {
        insert(shaderHeaders, header, before);
        return build;
      };
      build.appendHeaderIfNotExists = function (header) {
        appendIfNotExists(shaderHeaders, header);
        return build;
      };
      build.appendBody = function (body) {
        append(shaderBodies, body);
        return build;
      };
      build.insertBody = function (body, before) {
        insert(shaderBodies, body, before);
        return build;
      };
      build.appendBodyIfNotExists = function (body) {
        appendIfNotExists(shaderBodies, body);
        return build;
      };
      return build;
    });

    // inf is precalculated here for use in some functions (e.g. log scale calculations)
    var vertexShaderBase = function vertexShaderBase(header, body) {
      return "\nprecision mediump float;\nfloat inf = 1.0 / 0.0;\n".concat(header, "\nvoid main() {\n    ").concat(body, "\n}");
    };
    var fragmentShaderBase = function fragmentShaderBase(header, body) {
      return "\nprecision mediump float;\n".concat(header, "\nvoid main() {\n    gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);\n    ").concat(body, "\n}");
    };

    var fillColor$2 = {
      header: "attribute vec4 aFillColor;\n             varying vec4 vFillColor;",
      body: "vFillColor = aFillColor;"
    };
    var strokeColor$2 = {
      header: "attribute vec4 aStrokeColor;\n             varying vec4 vStrokeColor;",
      body: "vStrokeColor = aStrokeColor;"
    };
    var circle$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = 2.0 * sqrt(aSize / 3.14159);\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var star$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = 4.0 * sqrt(aSize / 3.14159);\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var wye$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = 3.0 * sqrt(aSize / 3.14159);\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var square$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = sqrt(aSize);\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var diamond$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = sqrt(aSize);\n        gl_PointSize = 2.0 * (vSize + uStrokeWidth + 1.0);\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var triangle$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = sqrt((16.0 * aSize) / (3.0 * sqrt(3.0)));\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var cross$1 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aSize;\n        attribute float aDefined;\n\n        uniform float uStrokeWidth;\n\n        varying float vSize;\n        varying float vStrokeWidthRatio;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vSize = 3.0 * sqrt(aSize / 5.0);\n        vStrokeWidthRatio = uStrokeWidth / (vSize + uStrokeWidth + 1.0);\n        gl_PointSize = vSize + uStrokeWidth + 1.0;\n        gl_Position = vec4(aCrossValue, aMainValue, 0, 1);"
    };
    var candlestick$4 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aBandwidth;\n        attribute float aHighValue;\n        attribute float aOpenValue;\n        attribute float aCloseValue;\n        attribute float aLowValue;\n        attribute vec3 aCorner;\n        attribute float aDefined;\n\n        uniform vec2 uScreen;\n        uniform float uStrokeWidth;\n\n        varying float vColorIndicator;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vColorIndicator = sign(aCloseValue - aOpenValue);\n\n        float isPositiveY = (sign(aCorner.y) + 1.0) / 2.0;\n        float isNotPositiveY = 1.0 - isPositiveY;\n        float isExtremeY = abs(aCorner.y) - 1.0;\n        float isNotExtremeY = 1.0 - isExtremeY;\n        float yValue =\n         (isPositiveY * isExtremeY * aLowValue) +\n         (isPositiveY * isNotExtremeY * aCloseValue) +\n         (isNotPositiveY * isNotExtremeY * aOpenValue) +\n         (isNotPositiveY * isExtremeY * aHighValue);\n\n        float lineWidthXDirection = (isNotExtremeY * aCorner.x) + (isExtremeY * aCorner.z);\n\n        float bodyThickness = (aOpenValue == aCloseValue ? 1.0 : sign(aCloseValue - aOpenValue));\n        float lineWidthYDirection = (isNotExtremeY * bodyThickness * aCorner.y);\n\n        float bandwidthModifier = aBandwidth * aCorner.x / 2.0;\n\n        float xModifier = (uStrokeWidth * lineWidthXDirection / 2.0) + bandwidthModifier;\n        float yModifier = uStrokeWidth * lineWidthYDirection / 2.0;\n\n        gl_Position = vec4(aCrossValue, yValue, 0, 1);"
    };
    var ohlc$4 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aBandwidth;\n        attribute float aHighValue;\n        attribute float aOpenValue;\n        attribute float aCloseValue;\n        attribute float aLowValue;\n        attribute vec3 aCorner;\n        attribute float aDefined;\n\n        uniform vec2 uScreen;\n        uniform float uStrokeWidth;\n\n        varying float vColorIndicator;\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        vColorIndicator = sign(aCloseValue - aOpenValue);\n\n        float isPositiveY = (sign(aCorner.y) + 1.0) / 2.0;\n        float isNotPositiveY = 1.0 - isPositiveY;\n        float isExtremeY = abs(aCorner.y) - 1.0;\n        float isNotExtremeY = 1.0 - isExtremeY;\n        float yValue =\n            (isPositiveY * isExtremeY * aLowValue) +\n            (isPositiveY * isNotExtremeY * aCloseValue) +\n            (isNotPositiveY * isNotExtremeY * aOpenValue) +\n            (isNotPositiveY * isExtremeY * aHighValue);\n\n        float lineWidthXDirection = isExtremeY * aCorner.z;\n        float lineWidthYDirection = isNotExtremeY * aCorner.z;\n\n        float bandwidthModifier = isNotExtremeY * aCorner.x * aBandwidth / 2.0;\n\n        float xModifier = (uStrokeWidth * lineWidthXDirection / 2.0) + bandwidthModifier;\n        float yModifier = uStrokeWidth * lineWidthYDirection / 2.0;\n\n        gl_Position = vec4(aCrossValue, yValue, 0, 1);"
    };
    var bar$4 = {
      header: "\n        attribute float aCrossValue;\n        attribute float aBandwidth;\n        attribute float aMainValue;\n        attribute float aBaseValue;\n        attribute vec2 aCorner;\n        attribute float aDefined;\n\n        uniform vec2 uScreen;\n        uniform float uStrokeWidth;\n\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        float isBaseline = (1.0 - aCorner.y) / 2.0;\n        float yValue = (isBaseline * aBaseValue) + ((1.0 - isBaseline) * aMainValue);\n\n        float xModifier = aCorner.x * (aBandwidth) / 2.0;\n\n        gl_Position = vec4(aCrossValue, yValue, 0, 1);"
    };
    var errorBar$4 = {
      header: "\n        attribute vec3 aCorner;\n        attribute float aCrossValue;\n        attribute float aBandwidth;\n        attribute float aHighValue;\n        attribute float aLowValue;\n        attribute float aDefined;\n\n        uniform vec2 uScreen;\n        uniform float uStrokeWidth;\n\n        varying float vDefined;",
      body: "\n        vDefined = aDefined;\n        float isLow = (aCorner.y + 1.0) / 2.0;\n        float yValue = isLow * aLowValue + (1.0 - isLow) * aHighValue;\n\n        float isEdgeCorner = abs(aCorner.x);\n        float lineWidthXDirection = (1.0 - isEdgeCorner) * aCorner.z;\n        float lineWidthYDirection = isEdgeCorner * aCorner.z;\n\n        gl_Position = vec4(aCrossValue, yValue, 0, 1);\n\n        float xModifier = (uStrokeWidth * lineWidthXDirection) + (aBandwidth * aCorner.x / 2.0);\n        float yModifier = (uStrokeWidth * lineWidthYDirection);"
    };
    var area$4 = {
      header: "\n        attribute vec3 aCorner;\n        attribute float aCrossValue;\n        attribute float aMainValue;\n        attribute float aCrossNextValue;\n        attribute float aMainNextValue;\n        attribute float aBaseValue;\n        attribute float aBaseNextValue;\n        attribute float aDefined;\n        attribute float aDefinedNext;\n\n        varying float vDefined;\n\n        float when_lt(float a, float b) {\n            return max(sign(b - a), 0.0);\n        }\n\n        float and(float a, float b) {\n            return a * b;\n        }",
      body: "\n        vDefined = aDefined * aDefinedNext;\n        gl_Position = vec4(0, 0, 0, 1);\n\n        float hasIntercepted = when_lt((aMainNextValue - aBaseNextValue) * (aMainValue - aBaseValue), 0.0);\n        float useIntercept = and(aCorner.z, hasIntercepted);\n\n        float yGradient = (aMainNextValue - aMainValue) / (aCrossNextValue - aCrossValue);\n        float yConstant = aMainNextValue - (yGradient * aCrossNextValue);\n\n        float y0Gradient = (aBaseNextValue - aBaseValue) / (aCrossNextValue - aCrossValue);\n        float y0Constant = aBaseNextValue - (y0Gradient * aCrossNextValue);\n\n        float denominator = (yGradient - y0Gradient) + step(abs(yGradient - y0Gradient), 0.0);\n        float interceptXValue = (y0Constant - yConstant) / denominator;\n        float interceptYValue = (yGradient * interceptXValue) + yConstant;\n\n        gl_Position = vec4(interceptXValue * useIntercept, interceptYValue * useIntercept, 0, 1);\n\n        gl_Position.x += (1.0 - useIntercept) * ((aCorner.x * aCrossNextValue) + ((1.0 - aCorner.x) * aCrossValue));\n        gl_Position.y += (1.0 - useIntercept) * (1.0 - aCorner.y) * ((aCorner.x * aMainNextValue) + ((1.0 - aCorner.x) * aMainValue));\n        gl_Position.y += (1.0 - useIntercept) * aCorner.y * ((aCorner.x * aBaseNextValue) + ((1.0 - aCorner.x) * aBaseValue));"
    };
    var boxPlot$4 = {
      header: "\n        attribute vec4 aCorner;\n        attribute float aCrossValue;\n        attribute float aBandwidth;\n        attribute float aCapWidth;\n        attribute float aHighValue;\n        attribute float aUpperQuartileValue;\n        attribute float aMedianValue;\n        attribute float aLowerQuartileValue;\n        attribute float aLowValue;\n        attribute float aDefined;\n\n        uniform vec2 uScreen;\n        uniform float uStrokeWidth;\n\n        varying float vDefined;\n    ",
      body: "\n        vDefined = aDefined;\n        float isExtremeY = sign(abs(aCorner.y) - 2.0) + 1.0;\n        float isNotExtremeY = 1.0 - isExtremeY;\n\n        float isNonZeroY = abs(sign(aCorner.y));\n        float isZeroY = 1.0 - isNonZeroY;\n\n        float isQuartileY = isNotExtremeY * isNonZeroY;\n\n        float isPositiveY = (sign(aCorner.y + 0.5) + 1.0) / 2.0;\n        float isNegativeY = 1.0 - isPositiveY;\n\n        float yValue =\n          (isExtremeY * isNegativeY) * aHighValue +\n          (isQuartileY * isNegativeY) * aUpperQuartileValue +\n          isZeroY * aMedianValue +\n          (isQuartileY * isPositiveY) * aLowerQuartileValue +\n          (isExtremeY * isPositiveY) * aLowValue;\n\n        gl_Position = vec4(aCrossValue, yValue, 0, 1);\n\n        float isHorizontal = aCorner.w;\n        float isVertical = 1.0 - isHorizontal;\n\n        float xDisplacement = aCorner.x * (isExtremeY * aCapWidth + isNotExtremeY * aBandwidth) / 2.0;\n\n        float xModifier = (isVertical * uStrokeWidth * aCorner.z / 2.0) + xDisplacement;\n        float yModifier = isHorizontal * uStrokeWidth * aCorner.z / 2.0;"
    };

    var circle = {
      header: "\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        float distance = length(2.0 * gl_PointCoord - 1.0);\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);\n        if (distance > 1.0 || vDefined < 0.5) {\n            discard;\n            return;\n        }"
    };

    // See https://iquilezles.org/www/articles/distfunctions2d/distfunctions2d.htm.
    var star = {
      header: "\n        varying float vSize;\n        varying float vDefined;\n\n        // anterior, exterior angles\n        float an = 0.628319;\n        vec2 acs = vec2(0.809017, 0.587786); // (cos, sin)\n        float en = 0.952000;\n        vec2 ecs = vec2(0.580055, 0.814577);\n    ",
      body: "\n        float canFill = 1.0;\n\n        vec2 p = 2.0 * gl_PointCoord - 1.0;\n        p.y *= -1.0;\n\n        // sector\n        float bn = mod(atan(p.x, p.y), 2.0 * an) - an;\n        p = length(p) * vec2(cos(bn), abs(sin(bn)));\n\n        p -= acs;\n        p += ecs * clamp(-dot(p, ecs), 0.0, acs.y / ecs.y);\n        float d = length(p) * sign(p.x);\n\n        float distance = 1.0 + d;\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);\n        if (distance > 1.0 || vDefined < 0.5) {\n            discard;\n            return;\n        }"
    };
    var wye = {
      header: "\n        varying float vSize;\n        varying float vDefined;\n    ",
      body: "\n        float canFill = 1.0;\n\n        vec2 p = 2.0 * gl_PointCoord - 1.0;\n        p.y *= -1.0;\n\n        // sector\n        float an = 3.141593 / 3.0;\n        float bn = mod(atan(p.x, p.y), 2.0 * an) - an;\n        p = length(p) * vec2(cos(bn), abs(sin(bn)));\n\n        // box\n        vec2 d = abs(p) - vec2(0.9, 0.35);\n        float sdf = length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);\n\n        float distance = 1.0 + sdf;\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);\n        if (distance > 1.0 || vDefined < 0.5) {\n            discard;\n            return;\n        }"
    };
    var square = {
      header: "\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        if (vDefined < 0.5) {\n            discard;\n        }\n        vec2 pointCoordTransform = 2.0 * gl_PointCoord - 1.0;\n        float distance = max(abs(pointCoordTransform.x), abs(pointCoordTransform.y));\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);"
    };

    // Diamond is symmetrical about the x, and y axes, so only consider x, y > 0.
    // (x, y) are the coordinates of the fragment within the gl point (after
    // transformed to be [-1, 1]).
    // a, b control the width, height of the triangle, so diamond is 2a, 2b.
    // Line L is a ray from the origin through (x, y), the distance function is then
    // the distance to (x, y) divided by the distance to where L intersects with the
    // diamond, this makes the distance function < 1 inside, 1 on the boundary, and
    // > 1 outside the diamond.
    //    |
    // b ---
    //    |\             L
    //    | -\          /
    //    |   \        /
    //    |    \      /
    //    |     -\   /
    //    |       \ /
    // Y ---       X
    //    |       / -\
    //    |      /    \
    //    |     /      \
    // y ---   X        -\
    //    |   /           \
    //    |  /             \
    //    | /               -\
    //    |/                  \
    //    +----|---|-----------|---
    //         x   X           a
    var diamond = {
      header: "\n        varying float vSize;\n        varying float vDefined;\n        float a = 0.6;\n        float b = 1.0;\n    ",
      body: "\n        if (vDefined < 0.5) {\n            discard;\n        }\n\n        vec2 pointCoordTransform = 2.0 * gl_PointCoord - 1.0;\n\n        float x = abs(pointCoordTransform.x);\n        float y = abs(pointCoordTransform.y);\n\n        float X = (a * b * x) / (a * y + b * x);\n        float Y = (a * b * y) / (a * y + b * x);\n\n        float distance = length(vec2(x, y)) / length(vec2(X, Y));\n\n        if (distance > 1.0) {\n            discard;\n        }\n    "
    };
    var triangle = {
      header: "\n        varying float vSize;\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        vec2 pointCoordTransform = 2.0 * gl_PointCoord - 1.0;\n        float topEdgesDistance = abs(pointCoordTransform.x) - ((pointCoordTransform.y - 0.6) / sqrt(3.0));\n        float bottomEdgeDistance = pointCoordTransform.y + 0.5;\n        float distance = max(topEdgesDistance, bottomEdgeDistance);\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);\n        if (distance > 1.0 || vDefined < 0.5) {\n            discard;\n        }"
    };
    var cross = {
      header: "\n        varying float vSize;\n        varying float vStrokeWidthRatio;\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        vec2 pointCoordTransform = 2.0 * gl_PointCoord - 1.0;\n        float innerCornerDistance = min(abs(pointCoordTransform.x), abs(pointCoordTransform.y)) + 0.66 - vStrokeWidthRatio;\n        float outerEdgeDistance = max(abs(pointCoordTransform.x), abs(pointCoordTransform.y));\n        float distance = max(innerCornerDistance, outerEdgeDistance);\n        float canStroke = smoothstep(vSize - 2.0, vSize, distance * vSize);\n        if (distance > 1.0 || vDefined < 0.5) {\n            discard;\n        }"
    };
    var candlestick$3 = {
      header: "\n        varying float vColorIndicator;\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        float canStroke = 0.0;\n        if (vDefined < 0.5) {\n            discard;\n        }\n        gl_FragColor = vec4(0.4, 0.8, 0, 1);\n        if (vColorIndicator < 0.0) {\n            gl_FragColor = vec4(0.8, 0.4, 0, 1);\n        }"
    };
    var ohlc$3 = {
      header: "\n        varying float vColorIndicator;\n        varying float vDefined;",
      body: "\n        float canFill = 0.0;\n        float canStroke = 1.0;\n        if (vDefined < 0.5) {\n            discard;\n        }\n        gl_FragColor = vec4(0.4, 0.8, 0, 1);\n        if (vColorIndicator < 0.0) {\n            gl_FragColor = vec4(0.8, 0.4, 0, 1);\n        }"
    };
    var area$3 = {
      header: "\n        varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        float canStroke = 0.0;\n        if (vDefined < 0.5) {\n            discard;\n        }\n        gl_FragColor = vec4(0.86, 0.86, 0.86, 1);"
    };
    var boxPlot$3 = {
      header: "\n        varying float vDefined;\n    ",
      body: "\n        float canFill = 0.0;\n        float canStroke = 1.0;\n\n        if (vDefined < 0.5) {\n            discard;\n        }"
    };
    var errorBar$3 = {
      header: "varying float vDefined;",
      body: "\n        float canFill = 0.0;\n        float canStroke = 1.0;\n        if (vDefined < 0.5) {\n            discard;\n        }"
    };
    var bar$3 = {
      header: "varying float vDefined;",
      body: "\n        float canFill = 1.0;\n        float canStroke = 0.0;\n\n        gl_FragColor = vec4(0.60, 0.60, 0.60, 1.0);\n\n        if (vDefined < 0.5) {\n            discard;\n        }"
    };
    var fillColor$1 = {
      header: "varying vec4 vFillColor;",
      body: "gl_FragColor = (canFill * vFillColor) + ((1.0 - canFill) * gl_FragColor);"
    };
    var strokeColor$1 = {
      header: "varying vec4 vStrokeColor;",
      body: "gl_FragColor = (canStroke * vStrokeColor) + ((1.0 - canStroke) * gl_FragColor);"
    };

    var areaShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(area$4.header).appendBody(area$4.body);
      fragmentShader.appendHeader(area$3.header).appendBody(area$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var types = {
      BYTE: 5120,
      UNSIGNED_BYTE: 5121,
      SHORT: 5122,
      UNSIGNED_SHORT: 5123,
      FLOAT: 5126
    };
    function length(type) {
      switch (type) {
        case types.BYTE:
        case types.UNSIGNED_BYTE:
          return 1;
        case types.SHORT:
        case types.UNSIGNED_SHORT:
          return 2;
        case types.FLOAT:
          return 4;
        default:
          throw new Error("Unknown type ".concat(type));
      }
    }
    function getArrayViewConstructor(type) {
      switch (type) {
        case types.BYTE:
          return Int8Array;
        case types.UNSIGNED_BYTE:
          return Uint8Array;
        case types.SHORT:
          return Int16Array;
        case types.UNSIGNED_SHORT:
          return Uint16Array;
        case types.FLOAT:
          return Float32Array;
        default:
          throw new Error("Unknown type ".concat(type));
      }
    }

    var baseAttributeBuilder = (function () {
      var location = -1;
      var buffer = null;
      var size = 1; // per vertex
      var type = types.FLOAT;
      var normalized = false;
      var stride = 0;
      var offset = 0;
      var divisor = null;
      var baseAttribute = function baseAttribute(programBuilder) {
        var gl = programBuilder.context();
        if (buffer == null) {
          buffer = gl.createBuffer();
        }
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.vertexAttribPointer(location, size, type, normalized, stride, offset);
        gl.enableVertexAttribArray(location);
        var extInstancedArrays = programBuilder.extInstancedArrays();
        extInstancedArrays.vertexAttribDivisorANGLE(location, divisor != null ? divisor : programBuilder.subInstanceCount() > 0 ? 1 : 0);
      };
      baseAttribute.location = function () {
        if (!arguments.length) {
          return location;
        }
        location = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.buffer = function () {
        if (!arguments.length) {
          return buffer;
        }
        buffer = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.size = function () {
        if (!arguments.length) {
          return size;
        }
        size = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.type = function () {
        if (!arguments.length) {
          return type;
        }
        type = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.normalized = function () {
        if (!arguments.length) {
          return normalized;
        }
        normalized = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.stride = function () {
        if (!arguments.length) {
          return stride;
        }
        stride = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.offset = function () {
        if (!arguments.length) {
          return offset;
        }
        offset = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      baseAttribute.divisor = function () {
        if (!arguments.length) {
          return divisor;
        }
        divisor = arguments.length <= 0 ? undefined : arguments[0];
        return baseAttribute;
      };
      return baseAttribute;
    });

    var defaultArrayViewFactory = (function () {
      var type = types.FLOAT;
      var cachedArray = new Float32Array(0);
      var factory = function factory(requiredLength) {
        var ArrayType = getArrayViewConstructor(type);
        if (cachedArray.length > requiredLength) {
          cachedArray = new ArrayType(cachedArray.buffer, 0, requiredLength);
        } else if (cachedArray.length !== requiredLength) {
          cachedArray = new ArrayType(requiredLength);
        }
        return cachedArray;
      };
      factory.type = function () {
        if (!arguments.length) {
          return type;
        }
        if (type !== (arguments.length <= 0 ? undefined : arguments[0])) {
          type = arguments.length <= 0 ? undefined : arguments[0];
          var ArrayType = getArrayViewConstructor(type);
          cachedArray = new ArrayType(0);
        }
        return factory;
      };
      return factory;
    });

    var attributeProjector = (function () {
      var dirty = true;
      var size = 1; // per vertex
      var type = types.FLOAT;
      var arrayViewFactory = defaultArrayViewFactory();
      var value = function value(d, i) {
        return d;
      };
      var data = null;
      var projector = function projector() {
        var length = data.length;
        var projectedData = arrayViewFactory.type(type)(length * size);
        if (size > 1) {
          for (var i = 0; i < length; i++) {
            var componentValues = value(data[i], i);
            if (componentValues.length !== size) {
              throw new Error("Expected components array of size ".concat(size, ", recieved array with length ").concat(componentValues.length, "."));
            }
            for (var component = 0; component < size; component++) {
              projectedData[i * size + component] = componentValues[component];
            }
          }
        } else {
          for (var _i = 0; _i < length; _i++) {
            var componentValue = value(data[_i], _i);
            if (Array.isArray(componentValue)) {
              throw new Error("Expected a single component value, recieved array with length ".concat(componentValue.length, "."));
            }
            projectedData[_i] = componentValue;
          }
        }
        dirty = false;
        return projectedData;
      };
      projector.dirty = function () {
        return dirty;
      };
      projector.clear = function () {
        dirty = true;
      };
      projector.size = function () {
        if (!arguments.length) {
          return size;
        }
        size = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return projector;
      };
      projector.type = function () {
        if (!arguments.length) {
          return type;
        }
        type = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return projector;
      };
      projector.arrayViewFactory = function () {
        if (!arguments.length) {
          return arrayViewFactory;
        }
        arrayViewFactory = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return projector;
      };
      projector.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return projector;
      };
      projector.data = function () {
        if (!arguments.length) {
          return data;
        }
        data = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return projector;
      };
      return projector;
    });

    var webglAttribute = (function () {
      var base = baseAttributeBuilder();
      var projector = attributeProjector();
      var attribute = function attribute(programBuilder) {
        base.size(attribute.size()).type(attribute.type());
        base(programBuilder);
        if (!projector.dirty()) {
          return;
        }
        var projectedData = projector();
        var gl = programBuilder.context();
        gl.bindBuffer(gl.ARRAY_BUFFER, base.buffer());
        gl.bufferData(gl.ARRAY_BUFFER, projectedData, gl.DYNAMIC_DRAW);
      };
      attribute.clear = function () {
        base.buffer(null);
        projector.clear();
      };
      rebind(attribute, base, 'normalized', 'location', 'divisor');
      rebind(attribute, projector, 'data', 'value', 'size', 'type');
      return attribute;
    });

    var rebindCurry = (function (target, targetName, source, sourceName) {
      for (var _len = arguments.length, curriedArgs = new Array(_len > 4 ? _len - 4 : 0), _key = 4; _key < _len; _key++) {
        curriedArgs[_key - 4] = arguments[_key];
      }
      target[targetName] = function () {
        for (var _len2 = arguments.length, args = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
          args[_key2] = arguments[_key2];
        }
        var result = source[sourceName].apply(source, curriedArgs.concat(args));
        if (result === source) {
          return target;
        }
        return result;
      };
    });

    var webglSeriesArea = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(6);
      var xScale = baseScale();
      var yScale = baseScale();
      var decorate = function decorate() {};
      var cornerAttribute = webglAttribute().divisor(0).size(3).type(types.UNSIGNED_BYTE).data([[0, 0, 0], [0, 1, 0], [1, 1, 1], [0, 0, 1], [1, 0, 0], [1, 1, 0]]);
      program.buffers().attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = areaShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        decorate(program);
        program(numElements - 1);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'crossNextValueAttribute', program.buffers(), 'attribute', 'aCrossNextValue');
      rebindCurry(draw, 'mainValueAttribute', program.buffers(), 'attribute', 'aMainValue');
      rebindCurry(draw, 'mainNextValueAttribute', program.buffers(), 'attribute', 'aMainNextValue');
      rebindCurry(draw, 'baseValueAttribute', program.buffers(), 'attribute', 'aBaseValue');
      rebindCurry(draw, 'baseNextValueAttribute', program.buffers(), 'attribute', 'aBaseNextValue');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      rebindCurry(draw, 'definedNextAttribute', program.buffers(), 'attribute', 'aDefinedNext');
      return draw;
    });

    var circlePointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(circle$1.header).appendBody(circle$1.body);
      fragmentShader.appendHeader(circle.header).appendBody(circle.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var webglSeriesPoint = (function () {
      var program = programBuilder().mode(drawModes.POINTS);
      var xScale = baseScale();
      var yScale = baseScale();
      var type = circlePointShader();
      var decorate = function decorate() {};
      var draw = function draw(numElements) {
        program.vertexShader(type.vertex()).fragmentShader(type.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        decorate(program);
        program(numElements);
      };
      draw.type = function () {
        if (!arguments.length) {
          return type;
        }
        type = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'mainValueAttribute', program.buffers(), 'attribute', 'aMainValue');
      rebindCurry(draw, 'sizeAttribute', program.buffers(), 'attribute', 'aSize');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var lineWidthShader = (function () {
      var width = 1;
      var lineWidth = function lineWidth(program) {
        program.buffers().uniform('uStrokeWidth', uniform(width));
      };
      lineWidth.lineWidth = function () {
        if (!arguments.length) {
          return width;
        }
        width = arguments.length <= 0 ? undefined : arguments[0];
        return lineWidth;
      };
      return lineWidth;
    });

    var elementIndices = (function (initialData) {
      var buffer = null;
      var data = initialData;
      var dirty = true;
      var base = function base(programBuilder) {
        var gl = programBuilder.context();
        if (buffer == null) {
          buffer = gl.createBuffer();
        }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffer);
        if (!dirty) {
          return;
        }
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(data), gl.STATIC_DRAW);
        dirty = false;
      };
      base.clear = function () {
        buffer = null;
        dirty = true;
      };
      base.data = function () {
        if (!arguments.length) {
          return data;
        }
        dirty = true;
        data = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var webglSeriesLine = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(6);
      var xScale = baseScale();
      var yScale = baseScale();
      var decorate = function decorate() {};
      var lineWidth = lineWidthShader();

      /*
          Line segment from a to b has vertices A, B, C, D -
             A |-------| B
              | \     |
              |a  \  b|
              |     \ |
            D |-------| C
           |AD| = uStrokeWidth
          |AB| = |ab| + uStrokeWidth
           Fragment shader implemented using line segment SDF 
          simplified for starting at the origin (a) -
          https://www.iquilezles.org/www/articles/distfunctions2d/distfunctions2d.htm
      */
      var cornerAttribute = webglAttribute().divisor(0).size(4).type(types.BYTE).data([[-1, +1, 1, 0], [+1, +1, 0, 1], [+1, -1, 0, 1], [-1, -1, 1, 0]]);
      program.buffers().elementIndices(elementIndices([0, 1, 2, 2, 3, 0])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var vertexShader = shaderBuilder(vertexShaderBase);
        var fragmentShader = shaderBuilder(fragmentShaderBase);
        program.vertexShader(vertexShader).fragmentShader(fragmentShader);
        vertexShader.appendHeader("\n            attribute vec4 aCorner;\n            attribute float aCrossValue;\n            attribute float aCrossNextValue;\n            attribute float aMainValue;\n            attribute float aMainNextValue;\n            attribute float aDefined;\n            attribute float aDefinedNext;\n\n            uniform float uStrokeWidth;\n            uniform vec2 uScreen;\n\n            varying float vLength;\n            varying vec2 vPosition;\n        ");
        vertexShader.appendBody("\n            vec4 value = vec4(aCrossValue, aMainValue, 0.0, 1.0);\n            vec4 nextValue = vec4(aCrossNextValue, aMainNextValue, 0.0, 1.0);\n        ");
        xScale(program, 'value', 0);
        xScale(program, 'nextValue', 0);
        yScale(program, 'value', 1);
        yScale(program, 'nextValue', 1);
        vertexShader.appendBody("\n            vec2 position = aCorner[2] * value.xy + aCorner[3] * nextValue.xy;\n\n            vec2 direction = normalize((nextValue.xy - value.xy) * uScreen);\n            vec2 normal = vec2(direction.y, -direction.x);\n            vec2 padding = ((uStrokeWidth / 2.0) / (uScreen / 2.0));\n            \n            padding *= aDefined * aDefinedNext;\n            position += (aCorner[0] * direction + aCorner[1] * normal) * padding;\n\n            gl_Position = vec4(position.x, position.y, 0.0, 1.0);\n\n            vLength = length((nextValue.xy - value.xy) * (uScreen / 2.0));\n            vPosition = aCorner.xy * (uStrokeWidth / 2.0);\n            vPosition.x += aCorner[3] * vLength;\n        ");

        // all fragment shader inputs are pixel denominated

        fragmentShader.appendHeader("\n            uniform float uStrokeWidth;\n            varying float vLength;\n            varying vec2 vPosition;\n\n            float canFill = 0.0;\n            float canStroke = 1.0;\n        ");
        fragmentShader.appendBody("\n            vec2 position = vPosition;\n            position.x -= clamp(position.x, 0.0, vLength);\n            float sdf = length(position) - uStrokeWidth / 2.0;\n            if (sdf > 0.5) {\n                discard;\n            }\n        ");
        lineWidth(program);
        decorate(program);
        program(numElements - 1);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebind(draw, lineWidth, 'lineWidth');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'crossNextValueAttribute', program.buffers(), 'attribute', 'aCrossNextValue');
      rebindCurry(draw, 'mainValueAttribute', program.buffers(), 'attribute', 'aMainValue');
      rebindCurry(draw, 'mainNextValueAttribute', program.buffers(), 'attribute', 'aMainNextValue');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      rebindCurry(draw, 'definedNextAttribute', program.buffers(), 'attribute', 'aDefinedNext');
      return draw;
    });

    var ohlcShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(ohlc$4.header).appendBody(ohlc$4.body);
      fragmentShader.appendHeader(ohlc$3.header).appendBody(ohlc$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var webglSeriesOhlc = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(18);
      var xScale = baseScale();
      var yScale = baseScale();
      var lineWidth = lineWidthShader();
      var decorate = function decorate() {};

      /*
       * x-y coordinate to locate the "corners" of the element.
       * X: -1: LEFT, 0: MIDDLE, 1: RIGHT
       * Y: -2: HIGH, -1: OPEN, 1: CLOSE, 2: LOW
       * Z - Follows convention for X/Y (appropriate direction will be selected by the shader): -1: LEFT/TOP, 1: RIGHT/BOTTOM
       */
      var cornerAttribute = webglAttribute().divisor(0).size(3).type(types.BYTE).data([
      // Main stem
      [0, -2, -1], [0, -2, 1], [0, 2, 1], [0, 2, -1],
      // Open bar
      [-1, -1, -1], [-1, -1, 1], [0, -1, 1], [0, -1, -1],
      // Close bar
      [1, 1, 1], [0, 1, 1], [0, 1, -1], [1, 1, -1]]);
      program.buffers().elementIndices(elementIndices([
      // Main stem
      0, 1, 2, 0, 3, 2,
      // Open bar
      4, 5, 6, 4, 7, 6,
      // Close bar
      8, 9, 10, 10, 11, 8])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = ohlcShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        lineWidth(program);
        program.vertexShader().appendBody("\n          gl_Position.x += xModifier / uScreen.x * 2.0;\n          gl_Position.y += yModifier / uScreen.y * 2.0;\n        ");
        decorate(program);
        program(numElements);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebind(draw, lineWidth, 'lineWidth');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'openValueAttribute', program.buffers(), 'attribute', 'aOpenValue');
      rebindCurry(draw, 'highValueAttribute', program.buffers(), 'attribute', 'aHighValue');
      rebindCurry(draw, 'lowValueAttribute', program.buffers(), 'attribute', 'aLowValue');
      rebindCurry(draw, 'closeValueAttribute', program.buffers(), 'attribute', 'aCloseValue');
      rebindCurry(draw, 'bandwidthAttribute', program.buffers(), 'attribute', 'aBandwidth');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var barShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(bar$4.header).appendBody(bar$4.body);
      fragmentShader.appendHeader(bar$3.header).appendBody(bar$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    //     βL            β            βR
    //     .-------------.------------.
    // (x-w/2, y1)    (x, y1)   (x+w/2, y1)
    //     |     \                    |
    //     |        \                 |
    //     |           \              |
    //     |              \           |
    //     |                 \        |
    //     |                    \     |
    //     |                       \  |
    //     αL            α            αR
    //     .-------------.------------.
    // (x-w/2, y0)     (x, y0)   (x+w/2, y0)

    // Drawing order
    // Triangle βL, αL, αR. (bottom)
    // β -> βL.
    // α -> αL.
    // α -> αR.

    // Triangle βL, αR, βR. (top)
    // β -> βL.
    // α -> αR.
    // β -> βR.

    var webglSeriesBar = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(6);
      var xScale = baseScale();
      var yScale = baseScale();
      var decorate = function decorate() {};
      var cornerAttribute = webglAttribute().divisor(0).size(2).type(types.BYTE).data([[-1, -1], [1, 1], [-1, 1], [1, -1]]);
      program.buffers().elementIndices(elementIndices([0, 1, 2, 0, 1, 3])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = barShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        program.vertexShader().appendBody("\n            gl_Position.x += xModifier / uScreen.x * 2.0;\n        ");
        decorate(program);
        program(numElements);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'mainValueAttribute', program.buffers(), 'attribute', 'aMainValue');
      rebindCurry(draw, 'baseValueAttribute', program.buffers(), 'attribute', 'aBaseValue');
      rebindCurry(draw, 'bandwidthAttribute', program.buffers(), 'attribute', 'aBandwidth');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var errorBarShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(errorBar$4.header).appendBody(errorBar$4.body);
      fragmentShader.appendHeader(errorBar$3.header).appendBody(errorBar$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var webglSeriesErrorBar = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(18);
      var xScale = baseScale();
      var yScale = baseScale();
      var decorate = function decorate() {};
      var lineWidth = lineWidthShader();

      /*
       * x-y coordinate to locate the "corners" of the element (ie errorbar). The `z` coordinate locates the corner relative to the line (this takes line width into account).
       * X: -1: LEFT, 0: MIDDLE, 1: RIGHT
       * Y: -1: HIGH, 1: LOW
       * Z: Follows X or Y convention, depending on the orientation of the line that the vertex is part of.
       */
      var cornerAttribute = webglAttribute().divisor(0).size(3).type(types.BYTE).data([
      // Main stem
      [0, 1, 1], [0, 1, -1], [0, -1, -1], [0, -1, 1],
      // Top cap
      [1, -1, 1], [1, -1, -1], [-1, -1, -1], [-1, -1, 1],
      // Bottom cap
      [-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]]);
      program.buffers().elementIndices(elementIndices([
      // Main stem
      0, 1, 2, 0, 3, 2,
      // Top cap
      4, 5, 6, 4, 7, 6,
      // Bottom cap
      8, 9, 10, 8, 11, 10])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = errorBarShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        lineWidth(program);
        program.vertexShader().appendBody("\n                gl_Position.x += xModifier / uScreen.x * 2.0;\n                gl_Position.y += yModifier / uScreen.y * 2.0;\n            ");
        decorate(program);
        program(numElements);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebind(draw, lineWidth, 'lineWidth');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'highValueAttribute', program.buffers(), 'attribute', 'aHighValue');
      rebindCurry(draw, 'lowValueAttribute', program.buffers(), 'attribute', 'aLowValue');
      rebindCurry(draw, 'bandwidthAttribute', program.buffers(), 'attribute', 'aBandwidth');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var candlestickShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(candlestick$4.header).appendBody(candlestick$4.body);
      fragmentShader.appendHeader(candlestick$3.header).appendBody(candlestick$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var webglSeriesCandlestick = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(12);
      var xScale = baseScale();
      var yScale = baseScale();
      var lineWidth = lineWidthShader();
      var decorate = function decorate() {};

      /*
       * x-y coordinate to locate the "corners" of the element.
       * X: -1: LEFT, 0: MIDDLE, 1: RIGHT
       * Y: -2: HIGH, -1: OPEN, 1: CLOSE, 2: LOW
       * Z: -1: LEFT, 1: RIGHT (only valid for HIGH/LOW corners)
       */
      var cornerAttribute = webglAttribute().divisor(0).size(3).type(types.BYTE).data([
      // Vertical line
      [0, 2, 1], [0, 2, -1], [0, -2, -1], [0, -2, 1],
      // Central box
      [1, -1, 0], [-1, -1, 0], [-1, 1, 0], [1, 1, 0]]);
      program.buffers().elementIndices(elementIndices([
      // Vertical line
      0, 1, 2, 0, 3, 2,
      // Central box
      4, 5, 6, 4, 7, 6])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = candlestickShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        lineWidth(program);
        program.vertexShader().appendBody("\n          gl_Position.x += xModifier / uScreen.x * 2.0;\n          gl_Position.y += yModifier / uScreen.y * 2.0;\n        ");
        decorate(program);
        program(numElements);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebind(draw, lineWidth, 'lineWidth');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'openValueAttribute', program.buffers(), 'attribute', 'aOpenValue');
      rebindCurry(draw, 'highValueAttribute', program.buffers(), 'attribute', 'aHighValue');
      rebindCurry(draw, 'lowValueAttribute', program.buffers(), 'attribute', 'aLowValue');
      rebindCurry(draw, 'closeValueAttribute', program.buffers(), 'attribute', 'aCloseValue');
      rebindCurry(draw, 'bandwidthAttribute', program.buffers(), 'attribute', 'aBandwidth');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var boxPlotShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(boxPlot$4.header).appendBody(boxPlot$4.body);
      fragmentShader.appendHeader(boxPlot$3.header).appendBody(boxPlot$3.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    //           αL1     α     αR1
    //            .------.------.
    //                   |
    //                   |
    //                   |
    //    βL2            β           βR2
    //     .-------------.------------.
    //     |                          |
    //     |                          |
    //     |                          |
    //     γL2            γ           γR2
    //     .-------------.------------.
    //     |                          |
    //     |                          |
    //     |                          |
    //    δL2            δ           δR2
    //     .-------------.------------.
    //                   |
    //                   |
    //                   |
    //           εL1     ε     εR1
    //            .------.------.

    // Line drawing order
    // αL1 -> αR1
    // α -> β
    // βL2 -> βR2
    // γL2 -> γR2
    // δL2 -> δR2
    // βL2 -> δL2
    // βR2 -> δR2
    // δ -> ε
    // εL1 -> εR1

    var webglSeriesBoxPlot = (function () {
      var program = programBuilder().mode(drawModes.TRIANGLES).subInstanceCount(54);
      var xScale = baseScale();
      var yScale = baseScale();
      var decorate = function decorate() {};
      var lineWidth = lineWidthShader();

      /*
       * x-y coordinate to locate the "corners" of the element (ie errorbar). The `z` coordinate locates the corner relative to the line (this takes line width into account).
       * X: -1: LEFT, 0: MIDDLE, 1: RIGHT
       * Y: -2: HIGH, -1: UPPER QUARTILE, 0: MEDIAN, 1: LOWER QUARTILE, 2: LOW
       * Z: Follows X or Y convention, depending on the orientation of the line that the vertex is part of.
       * W: Indicator to determine line orientation (needed because some corners are part of two lines). - 0: VERTICAL, 1: HORIZONTAL
       */
      var cornerAttribute = webglAttribute().divisor(0).size(4).type(types.BYTE).data([
      // Top cap line
      [-1, -2, -1, 1], [1, -2, -1, 1], [1, -2, 1, 1], [-1, -2, 1, 1],
      // Top whisker line
      [0, -2, -1, 0], [0, -2, 1, 0], [0, -1, 1, 0], [0, -1, -1, 0],
      // Upper quartile line
      [-1, -1, -1, 1], [1, -1, -1, 1], [1, -1, 1, 1], [-1, -1, 1, 1],
      // Median line
      [-1, 0, -1, 1], [1, 0, -1, 1], [1, 0, 1, 1], [-1, 0, 1, 1],
      // Lower quartile line
      [-1, 1, -1, 1], [1, 1, -1, 1], [1, 1, 1, 1], [-1, 1, 1, 1],
      // Left box vertical line
      [-1, -1, -1, 0], [-1, -1, 1, 0], [-1, 1, 1, 0], [-1, 1, -1, 0],
      // Right box vertical line
      [1, -1, -1, 0], [1, -1, 1, 0], [1, 1, 1, 0], [1, 1, -1, 0],
      // Bottom whisker line
      [0, 2, -1, 0], [0, 2, 1, 0], [0, 1, 1, 0], [0, 1, -1, 0],
      // Bottom cap line
      [-1, 2, -1, 1], [1, 2, -1, 1], [1, 2, 1, 1], [-1, 2, 1, 1]]);
      program.buffers().elementIndices(elementIndices([
      // Top cap line
      0, 1, 2, 0, 2, 3,
      // Top whisker line
      4, 5, 6, 4, 6, 7,
      // Upper quartile line
      8, 9, 10, 8, 10, 11,
      // Median line
      12, 13, 14, 12, 14, 15,
      // Lower quartile line
      16, 17, 18, 16, 18, 19,
      // Left box vertical line
      20, 21, 22, 20, 22, 23,
      // Right box vertical line
      24, 25, 26, 24, 26, 27,
      // Bottom whisker line
      28, 29, 30, 28, 30, 31,
      // Bottom cap line
      32, 33, 34, 32, 34, 35])).attribute('aCorner', cornerAttribute);
      var draw = function draw(numElements) {
        var shaderBuilder = boxPlotShader();
        program.vertexShader(shaderBuilder.vertex()).fragmentShader(shaderBuilder.fragment());
        xScale(program, 'gl_Position', 0);
        yScale(program, 'gl_Position', 1);
        lineWidth(program);
        program.vertexShader().appendBody("\n            gl_Position.x += xModifier / uScreen.x * 2.0;\n            gl_Position.y += yModifier / uScreen.y * 2.0;\n        ");
        decorate(program);
        program(numElements);
      };
      draw.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      draw.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return draw;
      };
      rebind(draw, program, 'context', 'pixelRatio');
      rebind(draw, lineWidth, 'lineWidth');
      rebindCurry(draw, 'crossValueAttribute', program.buffers(), 'attribute', 'aCrossValue');
      rebindCurry(draw, 'highValueAttribute', program.buffers(), 'attribute', 'aHighValue');
      rebindCurry(draw, 'upperQuartileValueAttribute', program.buffers(), 'attribute', 'aUpperQuartileValue');
      rebindCurry(draw, 'medianValueAttribute', program.buffers(), 'attribute', 'aMedianValue');
      rebindCurry(draw, 'lowerQuartileValueAttribute', program.buffers(), 'attribute', 'aLowerQuartileValue');
      rebindCurry(draw, 'lowValueAttribute', program.buffers(), 'attribute', 'aLowValue');
      rebindCurry(draw, 'bandwidthAttribute', program.buffers(), 'attribute', 'aBandwidth');
      rebindCurry(draw, 'capAttribute', program.buffers(), 'attribute', 'aCapWidth');
      rebindCurry(draw, 'definedAttribute', program.buffers(), 'attribute', 'aDefined');
      return draw;
    });

    var webglAdjacentAttribute = (function () {
      var minOffset = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
      var maxOffset = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;
      if (minOffset > 0 || maxOffset < 0) {
        throw new Error("Offset values (".concat(minOffset, " & ").concat(maxOffset, ") must straddle 0 "));
      }
      var base = baseAttributeBuilder();
      var projector = attributeProjector();
      var adjacentAttribute = function adjacentAttribute(programBuilder) {
        var elementSize = adjacentAttribute.size() * length(adjacentAttribute.type());
        var bufferOffset = Math.abs(minOffset) * elementSize;
        base.offset(bufferOffset).size(adjacentAttribute.size()).type(adjacentAttribute.type());
        base(programBuilder);
        if (!projector.dirty()) {
          return;
        }
        var projectedData = projector();
        var bufferPadding = maxOffset * elementSize;
        var bufferLength = bufferOffset + projectedData.length * length(adjacentAttribute.type()) + bufferPadding;
        var gl = programBuilder.context();
        gl.bindBuffer(gl.ARRAY_BUFFER, base.buffer());
        gl.bufferData(gl.ARRAY_BUFFER, bufferLength, gl.DYNAMIC_DRAW);
        gl.bufferSubData(gl.ARRAY_BUFFER, bufferOffset, projectedData);
      };
      adjacentAttribute.offset = function (offset) {
        if (minOffset > offset || offset > maxOffset) {
          throw new Error("Requested offset ".concat(offset, " exceeds bounds (").concat(minOffset, " & ").concat(maxOffset, ") "));
        }
        var offsetAttribute = function offsetAttribute(programBuilder) {
          base.offset((offset - minOffset) * adjacentAttribute.size() * length(adjacentAttribute.type()));
          base(programBuilder);
        };
        rebind(offsetAttribute, adjacentAttribute, 'clear', 'location');
        return offsetAttribute;
      };
      adjacentAttribute.clear = function () {
        base.buffer(null);
        projector.clear();
      };
      rebind(adjacentAttribute, base, 'normalized', 'location', 'divisor');
      rebind(adjacentAttribute, projector, 'data', 'value', 'size', 'type');
      return adjacentAttribute;
    });

    var linear = (function () {
      var base = baseScale();
      var prefix = function prefix(component) {
        return "linear".concat(component);
      };
      var scale = function scale(programBuilder, identifier, component) {
        programBuilder.vertexShader().appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Offset;")).appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Scale;")).appendBody("".concat(identifier, " = ").concat(identifier, " + ").concat(prefix(component), "Offset;")).appendBody("".concat(identifier, " = ").concat(identifier, " * ").concat(prefix(component), "Scale;"));
        var domainSize = base.domain()[1] - base.domain()[0];
        var rangeSize = base.range()[1] - base.range()[0];
        var translate = base.range()[0] * (domainSize / rangeSize) - base.domain()[0];
        var scaleFactor = rangeSize / domainSize;
        var offset = [0, 0, 0, 0];
        var scale = [1, 1, 1, 1];
        offset[component] = translate;
        scale[component] = scaleFactor;
        programBuilder.buffers().uniform("".concat(prefix(component), "Offset"), uniform(offset)).uniform("".concat(prefix(component), "Scale"), uniform(scale));
      };
      rebindAll(scale, base);
      return scale;
    });

    var log = (function () {
      var glBase = baseScale();
      var base = 10;
      function log(v, base) {
        return Math.log10(v) / Math.log10(base);
      }
      var prefix = function prefix(component) {
        return "log".concat(component);
      };
      var scale = function scale(programBuilder, identifier, component) {
        var logPart = "".concat(prefix(component), "Offset + (").concat(prefix(component), "Scale * clamp(log(").concat(identifier, ") / log(").concat(prefix(component), "Base), -inf, inf))");
        programBuilder.vertexShader().appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Offset;")).appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Scale;")).appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Include;")).appendHeaderIfNotExists("uniform float ".concat(prefix(component), "Base;")).appendBody("".concat(identifier, " = (").concat(prefix(component), "Include * (").concat(logPart, ")) + ((1.0 - ").concat(prefix(component), "Include) * ").concat(identifier, ");"));
        var domainSize = log(glBase.domain()[1], base) - log(glBase.domain()[0], base);
        var rangeSize = glBase.range()[1] - glBase.range()[0];
        var scaleFactor = rangeSize / domainSize;
        var translate = glBase.range()[0] - scaleFactor * log(glBase.domain()[0], base);
        var offset = [0, 0, 0, 0];
        var scale = [0, 0, 0, 0];
        var include = [0, 0, 0, 0];
        offset[component] = translate;
        scale[component] = scaleFactor;
        include[component] = 1;
        programBuilder.buffers().uniform("".concat(prefix(component), "Offset"), uniform(offset)).uniform("".concat(prefix(component), "Scale"), uniform(scale)).uniform("".concat(prefix(component), "Include"), uniform(include)).uniform("".concat(prefix(component), "Base"), uniform(base));
      };
      scale.base = function () {
        if (!arguments.length) {
          return base;
        }
        base = arguments.length <= 0 ? undefined : arguments[0];
        return scale;
      };
      rebindAll(scale, glBase);
      return scale;
    });

    var pow = (function () {
      var base = baseScale();
      var exponent = 1;
      function pow(b, e) {
        return Math.sign(b) * Math.pow(Math.abs(b), e);
      }
      var prefix = function prefix(component) {
        return "pow".concat(component);
      };
      var scale = function scale(programBuilder, identifier, component) {
        var powPart = "".concat(prefix(component), "Offset + (").concat(prefix(component), "Scale * sign(").concat(identifier, ") * pow(abs(").concat(identifier, "), vec4(").concat(prefix(component), "Exp)))");
        programBuilder.vertexShader().appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Offset;")).appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Scale;")).appendHeaderIfNotExists("uniform vec4 ".concat(prefix(component), "Include;")).appendHeaderIfNotExists("uniform float ".concat(prefix(component), "Exp;")).appendBody("".concat(identifier, " = (").concat(prefix(component), "Include * (").concat(powPart, ")) + ((1.0 - ").concat(prefix(component), "Include) * ").concat(identifier, ");"));
        var domainSize = pow(base.domain()[1], exponent) - pow(base.domain()[0], exponent);
        var rangeSize = base.range()[1] - base.range()[0];
        var scaleFactor = rangeSize / domainSize;
        var translate = base.range()[0] - scaleFactor * pow(base.domain()[0], exponent);
        var offset = [0, 0, 0, 0];
        var scale = [0, 0, 0, 0];
        var include = [0, 0, 0, 0];
        offset[component] = translate;
        scale[component] = scaleFactor;
        include[component] = 1;
        programBuilder.buffers().uniform("".concat(prefix(component), "Offset"), uniform(offset)).uniform("".concat(prefix(component), "Scale"), uniform(scale)).uniform("".concat(prefix(component), "Include"), uniform(include)).uniform("".concat(prefix(component), "Exp"), uniform(exponent));
      };
      scale.exponent = function () {
        if (!arguments.length) {
          return exponent;
        }
        exponent = arguments.length <= 0 ? undefined : arguments[0];
        return scale;
      };
      rebindAll(scale, base);
      return scale;
    });

    // we compare the stringified 'copy' function of the scale to
    // determine the scale type.
    var scaleLinearCopy = d3Scale.scaleLinear().copy.toString();
    var scaleLogCopy = d3Scale.scaleLog().copy.toString();
    var scalePowCopy = d3Scale.scalePow().copy.toString();
    var scaleTimeCopy = d3Scale.scaleTime().copy.toString();

    // always return the same reference to hint to consumers that
    // it is a pure function
    var identity$3 = d3Scale.scaleIdentity();

    // offset date values to make the most of the float32 precision
    var epoch = Date.now();
    var reepoch = function reepoch(d) {
      return d - epoch;
    };
    var webglScaleMapper = (function (scale) {
      switch (scale.copy.toString()) {
        case scaleLinearCopy:
          {
            return {
              scale: identity$3,
              webglScale: linear().domain(scale.domain())
            };
          }
        case scaleTimeCopy:
          {
            return {
              scale: reepoch,
              webglScale: linear().domain(scale.domain().map(reepoch))
            };
          }
        case scaleLogCopy:
          {
            return {
              scale: identity$3,
              webglScale: log().domain(scale.domain()).base(scale.base())
            };
          }
        case scalePowCopy:
          {
            return {
              scale: identity$3,
              webglScale: pow().domain(scale.domain()).exponent(scale.exponent())
            };
          }
        default:
          {
            // always return a copy of the scale to hint to consumers
            // that it may be an impure function
            return {
              scale: scale.copy(),
              webglScale: linear().domain(scale.range())
            };
          }
      }
    });

    var squarePointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(square$1.header).appendBody(square$1.body);
      fragmentShader.appendHeader(square.header).appendBody(square.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var trianglePointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(triangle$1.header).appendBody(triangle$1.body);
      fragmentShader.appendHeader(triangle.header).appendBody(triangle.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var crossPointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(cross$1.header).appendBody(cross$1.body);
      fragmentShader.appendHeader(cross.header).appendBody(cross.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var diamondPointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(diamond$1.header).appendBody(diamond$1.body);
      fragmentShader.appendHeader(diamond.header).appendBody(diamond.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var starPointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(star$1.header).appendBody(star$1.body);
      fragmentShader.appendHeader(star.header).appendBody(star.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var wyePointShader = (function () {
      var vertexShader = shaderBuilder(vertexShaderBase);
      var fragmentShader = shaderBuilder(fragmentShaderBase);
      vertexShader.appendHeader(wye$1.header).appendBody(wye$1.body);
      fragmentShader.appendHeader(wye.header).appendBody(wye.body);
      return {
        vertex: function vertex() {
          return vertexShader;
        },
        fragment: function fragment() {
          return fragmentShader;
        }
      };
    });

    var webglSymbolMapper = (function (symbol) {
      switch (symbol) {
        case d3Shape.symbolCircle:
          return circlePointShader();
        case d3Shape.symbolSquare:
          return squarePointShader();
        case d3Shape.symbolTriangle:
          return trianglePointShader();
        case d3Shape.symbolCross:
          return crossPointShader();
        case d3Shape.symbolDiamond:
          return diamondPointShader();
        case d3Shape.symbolStar:
          return starPointShader();
        case d3Shape.symbolWye:
          return wyePointShader();
        default:
          throw new Error("Unrecognised symbol: ".concat(symbol));
      }
    });

    var constantAttribute = (function (initialValue) {
      var base = baseAttributeBuilder().divisor(1);
      var value = initialValue;
      var dirty = true;
      var constantAttribute = function constantAttribute(programBuilder) {
        base(programBuilder);
        if (!dirty) {
          return;
        }
        if (!Array.isArray(value)) {
          throw new Error("Expected an array, received: ".concat(value));
        }
        if (value.length !== base.size()) {
          throw new Error("Expected array of length: ".concat(base.size(), ", recieved array of length: ").concat(value.length));
        }
        var gl = programBuilder.context();
        gl["vertexAttrib".concat(value.length, "fv")](base.location(), value);
        gl.disableVertexAttribArray(base.location());
        dirty = false;
      };
      constantAttribute.clear = function () {
        dirty = true;
      };
      constantAttribute.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        dirty = true;
        return constantAttribute;
      };
      rebind(constantAttribute, base, 'normalized', 'size', 'location');
      return constantAttribute;
    });

    var fillColor = (function () {
      var initialValue = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [0, 0, 0, 1];
      var projectedAttribute = webglAttribute().size(4);
      var value = initialValue;
      var dirty = true;
      var fillColor = function fillColor(programBuilder) {
        programBuilder.vertexShader().appendHeaderIfNotExists(fillColor$2.header).appendBodyIfNotExists(fillColor$2.body);
        programBuilder.fragmentShader().appendHeaderIfNotExists(fillColor$1.header).appendBodyIfNotExists(fillColor$1.body);
        if (Array.isArray(value)) {
          programBuilder.buffers().attribute('aFillColor', constantAttribute(value).size(4));
        } else if (typeof value === 'function') {
          if (!dirty) {
            return;
          }

          // The following line is expensive and is the one we want to skip,
          // the rest aren't.
          projectedAttribute.value(value);
          programBuilder.buffers().attribute('aFillColor', projectedAttribute);
        } else {
          throw new Error("Expected value to be an array or function, received ".concat(value));
        }
        dirty = false;
      };
      fillColor.value = function () {
        if (!arguments.length) {
          return value;
        }
        if (value !== (arguments.length <= 0 ? undefined : arguments[0])) {
          value = arguments.length <= 0 ? undefined : arguments[0];
          dirty = true;
        }
        return fillColor;
      };
      rebind(fillColor, projectedAttribute, 'data');
      return fillColor;
    });

    var strokeColor = (function () {
      var initialValue = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [0, 0, 0, 1];
      var projectedAttribute = webglAttribute().size(4);
      var value = initialValue;
      var dirty = true;
      var strokeColor = function strokeColor(programBuilder) {
        programBuilder.vertexShader().appendHeaderIfNotExists(strokeColor$2.header).appendBodyIfNotExists(strokeColor$2.body);
        programBuilder.fragmentShader().appendHeaderIfNotExists(strokeColor$1.header).appendBodyIfNotExists(strokeColor$1.body);
        if (Array.isArray(value)) {
          programBuilder.buffers().attribute('aStrokeColor', constantAttribute(value).size(4));
        } else if (typeof value === 'function') {
          if (!dirty) {
            return;
          }

          // The following line is expensive and is the one we want to skip,
          // the rest aren't.
          projectedAttribute.value(value);
          programBuilder.buffers().attribute('aStrokeColor', projectedAttribute);
        } else {
          throw new Error("Expected value to be an array or function, received ".concat(value));
        }
        dirty = false;
      };
      strokeColor.value = function () {
        if (!arguments.length) {
          return value;
        }
        if (value !== (arguments.length <= 0 ? undefined : arguments[0])) {
          value = arguments.length <= 0 ? undefined : arguments[0];
          dirty = true;
        }
        return strokeColor;
      };
      rebind(strokeColor, projectedAttribute, 'data');
      return strokeColor;
    });

    var line = (function () {
      var base = xyBase();
      var crossValueAttribute = webglAdjacentAttribute(0, 1);
      var crossNextValueAttribute = crossValueAttribute.offset(1);
      var mainValueAttribute = webglAdjacentAttribute(0, 1);
      var mainNextValueAttribute = mainValueAttribute.offset(1);
      var definedAttribute = webglAdjacentAttribute(0, 1).type(types.UNSIGNED_BYTE);
      var definedNextAttribute = definedAttribute.offset(1);
      var draw = webglSeriesLine().crossValueAttribute(crossValueAttribute).crossNextValueAttribute(crossNextValueAttribute).mainValueAttribute(mainValueAttribute).mainNextValueAttribute(mainNextValueAttribute).definedAttribute(definedAttribute).definedNextAttribute(definedNextAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var line = function line(data) {
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          if (base.orient() === 'vertical') {
            crossValueAttribute.value(function (d, i) {
              return xScale.scale(base.crossValue()(d, i));
            }).data(data);
          } else {
            crossValueAttribute.value(function (d, i) {
              return xScale.scale(base.mainValue()(d, i));
            }).data(data);
          }
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          if (base.orient() === 'vertical') {
            mainValueAttribute.value(function (d, i) {
              return yScale.scale(base.mainValue()(d, i));
            }).data(data);
          } else {
            mainValueAttribute.value(function (d, i) {
              return yScale.scale(base.crossValue()(d, i));
            }).data(data);
          }
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      line.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return line;
      };
      line.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return line;
      };
      rebindAll(line, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(line, draw, 'context', 'lineWidth', 'pixelRatio');
      return line;
    });

    var seriesSvgPoint = (function () {
      var symbol = d3Shape.symbol();
      var base = xyBase();
      var join = dataJoin('g', 'point');
      var containerTransform = function containerTransform(origin) {
        return 'translate(' + origin[0] + ', ' + origin[1] + ')';
      };
      var point = function point(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        selection.each(function (data, index, group) {
          var filteredData = data.filter(base.defined());
          var g = join(d3Selection.select(group[index]), filteredData);
          g.enter().attr('transform', function (d, i) {
            return containerTransform(base.values(d, i).origin);
          }).attr('fill', colors.gray).attr('stroke', colors.black).append('path');
          g.attr('transform', function (d, i) {
            return containerTransform(base.values(d, i).origin);
          }).select('path').attr('d', symbol);
          base.decorate()(g, data, index);
        });
      };
      rebindAll(point, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(point, join, 'key');
      rebind(point, symbol, 'type', 'size');
      return point;
    });

    var seriesCanvasPoint = (function () {
      var symbol = d3Shape.symbol();
      var base = xyBase();
      var point = function point(data) {
        var filteredData = data.filter(base.defined());
        var context = symbol.context();
        filteredData.forEach(function (d, i) {
          context.save();
          var values = base.values(d, i);
          context.translate(values.origin[0], values.origin[1]);
          context.beginPath();
          context.strokeStyle = colors.black;
          context.fillStyle = colors.gray;
          base.decorate()(context, d, i);
          symbol(d, i);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebindAll(point, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(point, symbol, 'size', 'type', 'context');
      return point;
    });

    var point = (function () {
      var base = xyBase();
      var size = functor$2(64);
      var type = d3Shape.symbolCircle;
      var crossValueAttribute = webglAttribute();
      var mainValueAttribute = webglAttribute();
      var sizeAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var definedAttribute = webglAttribute().type(types.UNSIGNED_BYTE);
      var draw = webglSeriesPoint().crossValueAttribute(crossValueAttribute).mainValueAttribute(mainValueAttribute).sizeAttribute(sizeAttribute).definedAttribute(definedAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var point = function point(data) {
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          sizeAttribute.value(function (d, i) {
            return size(d, i);
          }).data(data);
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          if (base.orient() === 'vertical') {
            crossValueAttribute.value(function (d, i) {
              return xScale.scale(base.crossValue()(d, i));
            }).data(data);
          } else {
            crossValueAttribute.value(function (d, i) {
              return xScale.scale(base.mainValue()(d, i));
            }).data(data);
          }
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          if (base.orient() === 'vertical') {
            mainValueAttribute.value(function (d, i) {
              return yScale.scale(base.mainValue()(d, i));
            }).data(data);
          } else {
            mainValueAttribute.value(function (d, i) {
              return yScale.scale(base.crossValue()(d, i));
            }).data(data);
          }
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).type(webglSymbolMapper(type)).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      point.size = function () {
        if (!arguments.length) {
          return size;
        }
        size = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return point;
      };
      point.type = function () {
        if (!arguments.length) {
          return type;
        }
        type = arguments.length <= 0 ? undefined : arguments[0];
        return point;
      };
      point.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return point;
      };
      point.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return point;
      };
      rebindAll(point, base, exclude('baseValue', 'bandwidth', 'align'));
      rebind(point, draw, 'context', 'pixelRatio');
      return point;
    });

    var bar$2 = (function () {
      var pathGenerator = shapeBar().x(0).y(0);
      var base = xyBase();
      var join = dataJoin('g', 'bar');
      var valueAxisDimension = function valueAxisDimension(generator) {
        return base.orient() === 'vertical' ? generator.height : generator.width;
      };
      var crossAxisDimension = function crossAxisDimension(generator) {
        return base.orient() === 'vertical' ? generator.width : generator.height;
      };
      var translation = function translation(origin) {
        return 'translate(' + origin[0] + ', ' + origin[1] + ')';
      };
      var bar = function bar(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        selection.each(function (data, index, group) {
          var orient = base.orient();
          if (orient !== 'vertical' && orient !== 'horizontal') {
            throw new Error('The bar series does not support an orientation of ' + orient);
          }
          var filteredData = data.filter(base.defined());
          var projectedData = filteredData.map(base.values);
          pathGenerator.width(0).height(0);
          if (base.orient() === 'vertical') {
            pathGenerator.verticalAlign('top');
            pathGenerator.horizontalAlign('center');
          } else {
            pathGenerator.horizontalAlign('right');
            pathGenerator.verticalAlign('center');
          }
          var g = join(d3Selection.select(group[index]), filteredData);

          // within the enter selection the pathGenerator creates a zero
          // height bar on the baseline. As a result, when used with a transition the bar grows
          // from y0 to y1 (y)
          g.enter().attr('transform', function (_, i) {
            return translation(projectedData[i].baseOrigin);
          }).attr('class', 'bar ' + base.orient()).attr('fill', colors.darkGray).append('path').attr('d', function (d, i) {
            crossAxisDimension(pathGenerator)(projectedData[i].width);
            return pathGenerator([d]);
          });

          // the container translation sets the origin to the 'tip'
          // of each bar as per the decorate pattern
          g.attr('transform', function (_, i) {
            return translation(projectedData[i].origin);
          }).select('path').attr('d', function (d, i) {
            crossAxisDimension(pathGenerator)(projectedData[i].width);
            valueAxisDimension(pathGenerator)(-projectedData[i].height);
            return pathGenerator([d]);
          });
          base.decorate()(g, filteredData, index);
        });
      };
      rebindAll(bar, base);
      rebind(bar, join, 'key');
      return bar;
    });

    var bar$1 = (function () {
      var base = xyBase();
      var pathGenerator = shapeBar().x(0).y(0);
      var valueAxisDimension = function valueAxisDimension(generator) {
        return base.orient() === 'vertical' ? generator.height : generator.width;
      };
      var crossAxisDimension = function crossAxisDimension(generator) {
        return base.orient() === 'vertical' ? generator.width : generator.height;
      };
      var bar = function bar(data) {
        var context = pathGenerator.context();
        var filteredData = data.filter(base.defined());
        var projectedData = filteredData.map(base.values);
        if (base.orient() === 'vertical') {
          pathGenerator.verticalAlign('top');
          pathGenerator.horizontalAlign('center');
        } else {
          pathGenerator.horizontalAlign('right');
          pathGenerator.verticalAlign('center');
        }
        projectedData.forEach(function (datum, i) {
          context.save();
          context.beginPath();
          context.translate(datum.origin[0], datum.origin[1]);
          context.fillStyle = colors.darkGray;
          context.strokeStyle = 'transparent';
          base.decorate()(context, datum.d, i);
          valueAxisDimension(pathGenerator)(-datum.height);
          crossAxisDimension(pathGenerator)(datum.width);
          pathGenerator([datum]);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebindAll(bar, base);
      rebind(bar, pathGenerator, 'context');
      return bar;
    });

    var bar = (function () {
      var base = xyBase();
      var crossValueAttribute = webglAttribute();
      var mainValueAttribute = webglAttribute();
      var baseValueAttribute = webglAttribute();
      var bandwidthAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var definedAttribute = webglAttribute().type(types.UNSIGNED_BYTE);
      var draw = webglSeriesBar().crossValueAttribute(crossValueAttribute).mainValueAttribute(mainValueAttribute).baseValueAttribute(baseValueAttribute).bandwidthAttribute(bandwidthAttribute).definedAttribute(definedAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var bar = function bar(data) {
        if (base.orient() !== 'vertical') {
          throw new Error("Unsupported orientation ".concat(base.orient()));
        }
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          bandwidthAttribute.value(function (d, i) {
            return base.bandwidth()(d, i);
          }).data(data);
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          crossValueAttribute.value(function (d, i) {
            return xScale.scale(base.crossValue()(d, i));
          }).data(data);
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          baseValueAttribute.value(function (d, i) {
            return yScale.scale(base.baseValue()(d, i));
          }).data(data);
          mainValueAttribute.value(function (d, i) {
            return yScale.scale(base.mainValue()(d, i));
          }).data(data);
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      bar.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return bar;
      };
      bar.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return bar;
      };
      rebindAll(bar, base, exclude('align'));
      rebind(bar, draw, 'context', 'pixelRatio');
      return bar;
    });

    var errorBarBase = (function () {
      var highValue = function highValue(d) {
        return d.high;
      };
      var lowValue = function lowValue(d) {
        return d.low;
      };
      var crossValue = function crossValue(d) {
        return d.cross;
      };
      var orient = 'vertical';
      var align = 'center';
      var bandwidth = function bandwidth() {
        return 5;
      };
      var base = createBase({
        decorate: function decorate() {},
        defined: function defined$1(d, i) {
          return defined(lowValue, highValue, crossValue)(d, i);
        },
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      base.values = function (d, i) {
        var width = bandwidth(d, i);
        var offset = alignOffset(align, width);
        var xScale = base.xScale();
        var yScale = base.yScale();
        if (orient === 'vertical') {
          var y = yScale(highValue(d, i));
          return {
            origin: [xScale(crossValue(d, i)) + offset, y],
            high: 0,
            low: yScale(lowValue(d, i)) - y,
            width: width
          };
        } else {
          var x = xScale(lowValue(d, i));
          return {
            origin: [x, yScale(crossValue(d, i)) + offset],
            high: xScale(highValue(d, i)) - x,
            low: 0,
            width: width
          };
        }
      };
      base.xValues = function () {
        return orient === 'vertical' ? [crossValue] : [highValue, lowValue];
      };
      base.yValues = function () {
        return orient !== 'vertical' ? [crossValue] : [highValue, lowValue];
      };
      base.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.lowValue = function () {
        if (!arguments.length) {
          return lowValue;
        }
        lowValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.highValue = function () {
        if (!arguments.length) {
          return highValue;
        }
        highValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.crossValue = function () {
        if (!arguments.length) {
          return crossValue;
        }
        crossValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.bandwidth = function () {
        if (!arguments.length) {
          return bandwidth;
        }
        bandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.align = function () {
        if (!arguments.length) {
          return align;
        }
        align = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var errorBar$2 = (function () {
      var base = errorBarBase();
      var join = dataJoin('g', 'error-bar');
      var pathGenerator = shapeErrorBar().value(0);
      var propagateTransition = function propagateTransition(maybeTransition) {
        return function (selection) {
          return isTransition(maybeTransition) ? selection.transition(maybeTransition) : selection;
        };
      };
      var containerTranslation = function containerTranslation(values) {
        return 'translate(' + values.origin[0] + ', ' + values.origin[1] + ')';
      };
      var errorBar = function errorBar(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        var transitionPropagator = propagateTransition(selection);
        selection.each(function (data, index, group) {
          var filteredData = data.filter(base.defined());
          var projectedData = filteredData.map(base.values);
          var g = join(d3Selection.select(group[index]), filteredData);
          g.enter().attr('stroke', colors.black).attr('fill', colors.gray).attr('transform', function (d, i) {
            return containerTranslation(base.values(d, i)) + ' scale(1e-6, 1)';
          }).append('path');
          pathGenerator.orient(base.orient());
          g.each(function (d, i, g) {
            var values = projectedData[i];
            pathGenerator.high(values.high).low(values.low).width(values.width);
            transitionPropagator(d3Selection.select(g[i])).attr('transform', containerTranslation(values) + ' scale(1)').select('path').attr('d', pathGenerator([d]));
          });
          base.decorate()(g, data, index);
        });
      };
      rebindAll(errorBar, base);
      rebind(errorBar, join, 'key');
      return errorBar;
    });

    var errorBar$1 = (function () {
      var base = errorBarBase();
      var pathGenerator = shapeErrorBar().value(0);
      var errorBar = function errorBar(data) {
        var filteredData = data.filter(base.defined());
        var context = pathGenerator.context();
        pathGenerator.orient(base.orient());
        filteredData.forEach(function (d, i) {
          context.save();
          var values = base.values(d, i);
          context.translate(values.origin[0], values.origin[1]);
          context.beginPath();
          context.strokeStyle = colors.black;
          context.fillStyle = colors.gray;
          base.decorate()(context, d, i);
          pathGenerator.high(values.high).width(values.width).low(values.low)([d]);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebindAll(errorBar, base);
      rebind(errorBar, pathGenerator, 'context');
      return errorBar;
    });

    var errorBar = (function () {
      var base = errorBarBase();
      var crossValueAttribute = webglAttribute();
      var highValueAttribute = webglAttribute();
      var lowValueAttribute = webglAttribute();
      var bandwidthAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var definedAttribute = webglAttribute().type(types.UNSIGNED_BYTE);
      var draw = webglSeriesErrorBar().crossValueAttribute(crossValueAttribute).highValueAttribute(highValueAttribute).lowValueAttribute(lowValueAttribute).bandwidthAttribute(bandwidthAttribute).definedAttribute(definedAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var errorBar = function errorBar(data) {
        if (base.orient() !== 'vertical') {
          throw new Error("Unsupported orientation ".concat(base.orient()));
        }
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          bandwidthAttribute.value(function (d, i) {
            return base.bandwidth()(d, i);
          }).data(data);
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          crossValueAttribute.value(function (d, i) {
            return xScale.scale(base.crossValue()(d, i));
          }).data(data);
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          highValueAttribute.value(function (d, i) {
            return yScale.scale(base.highValue()(d, i));
          }).data(data);
          lowValueAttribute.value(function (d, i) {
            return yScale.scale(base.lowValue()(d, i));
          }).data(data);
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      errorBar.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return errorBar;
      };
      errorBar.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return errorBar;
      };
      rebindAll(errorBar, base, exclude('align'));
      rebind(errorBar, draw, 'context', 'lineWidth', 'pixelRatio');
      return errorBar;
    });

    var area$2 = (function () {
      var base = xyBase();
      var areaData = d3Shape.area();
      var join = dataJoin('path', 'area');
      var area = function area(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        areaData.defined(base.defined());
        selection.each(function (data, index, group) {
          var projectedData = data.map(base.values);
          areaData.x(function (_, i) {
            return projectedData[i].transposedX;
          }).y(function (_, i) {
            return projectedData[i].transposedY;
          });
          var valueComponent = base.orient() === 'vertical' ? 'y' : 'x';
          areaData[valueComponent + '0'](function (_, i) {
            return projectedData[i].y0;
          });
          areaData[valueComponent + '1'](function (_, i) {
            return projectedData[i].y;
          });
          var path = join(d3Selection.select(group[index]), [data]);
          path.enter().attr('fill', colors.gray);
          path.attr('d', areaData);
          base.decorate()(path, data, index);
        });
      };
      rebindAll(area, base, exclude('bandwidth', 'align'));
      rebind(area, join, 'key');
      rebind(area, areaData, 'curve');
      return area;
    });

    var area$1 = (function () {
      var base = xyBase();
      var areaData = d3Shape.area();
      var area = function area(data) {
        var context = areaData.context();
        areaData.defined(base.defined());
        var projectedData = data.map(base.values);
        areaData.x(function (_, i) {
          return projectedData[i].transposedX;
        }).y(function (_, i) {
          return projectedData[i].transposedY;
        });
        var valueComponent = base.orient() === 'vertical' ? 'y' : 'x';
        areaData[valueComponent + '0'](function (_, i) {
          return projectedData[i].y0;
        });
        areaData[valueComponent + '1'](function (_, i) {
          return projectedData[i].y;
        });
        context.beginPath();
        context.fillStyle = colors.gray;
        context.strokeStyle = 'transparent';
        base.decorate()(context, data);
        areaData(data);
        context.fill();
        context.stroke();
        context.closePath();
      };
      rebindAll(area, base, exclude('bandwidth', 'align'));
      rebind(area, areaData, 'curve', 'context');
      return area;
    });

    var area = (function () {
      var base = xyBase();
      var crossValueAttribute = webglAdjacentAttribute(0, 1);
      var crossNextValueAttribute = crossValueAttribute.offset(1);
      var mainValueAttribute = webglAdjacentAttribute(0, 1);
      var mainNextValueAttribute = mainValueAttribute.offset(1);
      var baseValueAttribute = webglAdjacentAttribute(0, 1);
      var baseNextValueAttribute = baseValueAttribute.offset(1);
      var definedAttribute = webglAdjacentAttribute(0, 1).type(types.UNSIGNED_BYTE);
      var definedNextAttribute = definedAttribute.offset(1);
      var draw = webglSeriesArea().crossValueAttribute(crossValueAttribute).crossNextValueAttribute(crossNextValueAttribute).mainValueAttribute(mainValueAttribute).mainNextValueAttribute(mainNextValueAttribute).baseValueAttribute(baseValueAttribute).baseNextValueAttribute(baseNextValueAttribute).definedAttribute(definedAttribute).definedNextAttribute(definedNextAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var area = function area(data) {
        if (base.orient() !== 'vertical') {
          throw new Error("Unsupported orientation ".concat(base.orient()));
        }
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          crossValueAttribute.value(function (d, i) {
            return xScale.scale(base.crossValue()(d, i));
          }).data(data);
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          baseValueAttribute.value(function (d, i) {
            return yScale.scale(base.baseValue()(d, i));
          }).data(data);
          mainValueAttribute.value(function (d, i) {
            return yScale.scale(base.mainValue()(d, i));
          }).data(data);
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      area.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return area;
      };
      area.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return area;
      };
      rebindAll(area, base, exclude('bandwidth', 'align'));
      rebind(area, draw, 'context', 'pixelRatio');
      return area;
    });

    var ohlcBase$3 = (function () {
      var base;
      var crossValue = function crossValue(d) {
        return d.date;
      };
      var openValue = function openValue(d) {
        return d.open;
      };
      var highValue = function highValue(d) {
        return d.high;
      };
      var lowValue = function lowValue(d) {
        return d.low;
      };
      var closeValue = function closeValue(d) {
        return d.close;
      };
      var bandwidth = function bandwidth() {
        return 5;
      };
      var align = 'center';
      var crossValueScaled = function crossValueScaled(d, i) {
        return base.xScale()(crossValue(d, i));
      };
      base = createBase({
        decorate: function decorate() {},
        defined: function defined$1(d, i) {
          return defined(crossValue, openValue, lowValue, highValue, closeValue)(d, i);
        },
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      base.values = function (d, i) {
        var closeRaw = closeValue(d, i);
        var openRaw = openValue(d, i);
        var width = bandwidth(d, i);
        var offset = alignOffset(align, width);
        var direction = '';
        if (closeRaw > openRaw) {
          direction = 'up';
        } else if (closeRaw < openRaw) {
          direction = 'down';
        }
        return {
          cross: crossValueScaled(d, i) + offset,
          open: base.yScale()(openRaw),
          high: base.yScale()(highValue(d, i)),
          low: base.yScale()(lowValue(d, i)),
          close: base.yScale()(closeRaw),
          width: width,
          direction: direction
        };
      };
      base.xValues = function () {
        return [crossValue];
      };
      base.yValues = function () {
        return [openValue, highValue, lowValue, closeValue];
      };
      base.crossValue = function () {
        if (!arguments.length) {
          return crossValue;
        }
        crossValue = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.openValue = function () {
        if (!arguments.length) {
          return openValue;
        }
        openValue = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.highValue = function () {
        if (!arguments.length) {
          return highValue;
        }
        highValue = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.lowValue = function () {
        if (!arguments.length) {
          return lowValue;
        }
        lowValue = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.yValue = base.closeValue = function () {
        if (!arguments.length) {
          return closeValue;
        }
        closeValue = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.bandwidth = function () {
        if (!arguments.length) {
          return bandwidth;
        }
        bandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.align = function () {
        if (!arguments.length) {
          return align;
        }
        align = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var ohlcBase$2 = (function (pathGenerator, seriesName) {
      var base = ohlcBase$3();
      var join = dataJoin('g', seriesName);
      var containerTranslation = function containerTranslation(values) {
        return 'translate(' + values.cross + ', ' + values.high + ')';
      };
      var propagateTransition = function propagateTransition(maybeTransition) {
        return function (selection) {
          return isTransition(maybeTransition) ? selection.transition(maybeTransition) : selection;
        };
      };
      var candlestick = function candlestick(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        var transitionPropagator = propagateTransition(selection);
        selection.each(function (data, index, group) {
          var filteredData = data.filter(base.defined());
          var g = join(d3Selection.select(group[index]), filteredData);
          g.enter().attr('transform', function (d, i) {
            return containerTranslation(base.values(d, i)) + ' scale(1e-6, 1)';
          }).append('path');
          g.each(function (d, i, g) {
            var values = base.values(d, i);
            var color = values.direction === 'up' ? colors.green : colors.red;
            var singleCandlestick = transitionPropagator(d3Selection.select(g[i])).attr('class', seriesName + ' ' + values.direction).attr('stroke', color).attr('fill', color).attr('transform', function () {
              return containerTranslation(values) + ' scale(1)';
            });
            pathGenerator.x(0).width(values.width).open(function () {
              return values.open - values.high;
            }).high(0).low(function () {
              return values.low - values.high;
            }).close(function () {
              return values.close - values.high;
            });
            singleCandlestick.select('path').attr('d', pathGenerator([d]));
          });
          base.decorate()(g, data, index);
        });
      };
      rebind(candlestick, join, 'key');
      rebindAll(candlestick, base);
      return candlestick;
    });

    var candlestick$2 = (function () {
      return ohlcBase$2(shapeCandlestick(), 'candlestick');
    });

    var ohlcBase$1 = (function (pathGenerator) {
      var base = ohlcBase$3();
      var candlestick = function candlestick(data) {
        var filteredData = data.filter(base.defined());
        var context = pathGenerator.context();
        filteredData.forEach(function (d, i) {
          context.save();
          var values = base.values(d, i);
          context.translate(values.cross, values.high);
          context.beginPath();
          pathGenerator.x(0).open(function () {
            return values.open - values.high;
          }).width(values.width).high(0).low(function () {
            return values.low - values.high;
          }).close(function () {
            return values.close - values.high;
          })([d]);
          var color = values.direction === 'up' ? colors.green : colors.red;
          context.strokeStyle = color;
          context.fillStyle = color;
          base.decorate()(context, d, i);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebind(candlestick, pathGenerator, 'context');
      rebindAll(candlestick, base);
      return candlestick;
    });

    var candlestick$1 = (function () {
      return ohlcBase$1(shapeCandlestick());
    });

    var ohlcBase = (function (pathGenerator) {
      var base = ohlcBase$3();
      var crossValueAttribute = webglAttribute();
      var openValueAttribute = webglAttribute();
      var highValueAttribute = webglAttribute();
      var lowValueAttribute = webglAttribute();
      var closeValueAttribute = webglAttribute();
      var bandwidthAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var definedAttribute = webglAttribute().type(types.UNSIGNED_BYTE);
      pathGenerator.crossValueAttribute(crossValueAttribute).openValueAttribute(openValueAttribute).highValueAttribute(highValueAttribute).lowValueAttribute(lowValueAttribute).closeValueAttribute(closeValueAttribute).bandwidthAttribute(bandwidthAttribute).definedAttribute(definedAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var candlestick = function candlestick(data) {
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          bandwidthAttribute.value(function (d, i) {
            return base.bandwidth()(d, i);
          }).data(data);
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          crossValueAttribute.value(function (d, i) {
            return xScale.scale(base.crossValue()(d, i));
          }).data(data);
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          openValueAttribute.value(function (d, i) {
            return yScale.scale(base.openValue()(d, i));
          }).data(data);
          highValueAttribute.value(function (d, i) {
            return yScale.scale(base.highValue()(d, i));
          }).data(data);
          lowValueAttribute.value(function (d, i) {
            return yScale.scale(base.lowValue()(d, i));
          }).data(data);
          closeValueAttribute.value(function (d, i) {
            return yScale.scale(base.closeValue()(d, i));
          }).data(data);
        }
        pathGenerator.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        pathGenerator(data.length);
      };
      candlestick.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return candlestick;
      };
      candlestick.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return candlestick;
      };
      rebindAll(candlestick, base, exclude('align'));
      rebind(candlestick, pathGenerator, 'context', 'lineWidth', 'pixelRatio');
      return candlestick;
    });

    var candlestick = (function () {
      return ohlcBase(webglSeriesCandlestick());
    });

    var boxPlotBase = (function () {
      var upperQuartileValue = function upperQuartileValue(d) {
        return d.upperQuartile;
      };
      var lowerQuartileValue = function lowerQuartileValue(d) {
        return d.lowerQuartile;
      };
      var highValue = function highValue(d) {
        return d.high;
      };
      var lowValue = function lowValue(d) {
        return d.low;
      };
      var crossValue = function crossValue(d) {
        return d.value;
      };
      var medianValue = function medianValue(d) {
        return d.median;
      };
      var orient = 'vertical';
      var align = 'center';
      var bandwidth = function bandwidth() {
        return 5;
      };
      var base = createBase({
        decorate: function decorate() {},
        defined: function defined$1(d, i) {
          return defined(lowValue, highValue, lowerQuartileValue, upperQuartileValue, crossValue, medianValue)(d, i);
        },
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      base.values = function (d, i) {
        var width = bandwidth(d, i);
        var offset = alignOffset(align, width);
        var xScale = base.xScale();
        var yScale = base.yScale();
        if (orient === 'vertical') {
          var y = yScale(highValue(d, i));
          return {
            origin: [xScale(crossValue(d, i)) + offset, y],
            high: 0,
            upperQuartile: yScale(upperQuartileValue(d, i)) - y,
            median: yScale(medianValue(d, i)) - y,
            lowerQuartile: yScale(lowerQuartileValue(d, i)) - y,
            low: yScale(lowValue(d, i)) - y,
            width: width
          };
        } else {
          var x = xScale(lowValue(d, i));
          return {
            origin: [x, yScale(crossValue(d, i)) + offset],
            high: xScale(highValue(d, i)) - x,
            upperQuartile: xScale(upperQuartileValue(d, i)) - x,
            median: xScale(medianValue(d, i)) - x,
            lowerQuartile: xScale(lowerQuartileValue(d, i)) - x,
            low: 0,
            width: width
          };
        }
      };
      base.xValues = function () {
        return orient === 'vertical' ? [crossValue] : [upperQuartileValue, lowerQuartileValue, highValue, lowValue, medianValue];
      };
      base.yValues = function () {
        return orient !== 'vertical' ? [crossValue] : [upperQuartileValue, lowerQuartileValue, highValue, lowValue, medianValue];
      };
      base.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.lowerQuartileValue = function () {
        if (!arguments.length) {
          return lowerQuartileValue;
        }
        lowerQuartileValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.upperQuartileValue = function () {
        if (!arguments.length) {
          return upperQuartileValue;
        }
        upperQuartileValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.lowValue = function () {
        if (!arguments.length) {
          return lowValue;
        }
        lowValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.highValue = function () {
        if (!arguments.length) {
          return highValue;
        }
        highValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.crossValue = function () {
        if (!arguments.length) {
          return crossValue;
        }
        crossValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.medianValue = function () {
        if (!arguments.length) {
          return medianValue;
        }
        medianValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.bandwidth = function () {
        if (!arguments.length) {
          return bandwidth;
        }
        bandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return base;
      };
      base.align = function () {
        if (!arguments.length) {
          return align;
        }
        align = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      return base;
    });

    var boxPlot$2 = (function () {
      var base = boxPlotBase();
      var join = dataJoin('g', 'box-plot');
      var pathGenerator = shapeBoxPlot().value(0);
      var propagateTransition = function propagateTransition(maybeTransition) {
        return function (selection) {
          return isTransition(maybeTransition) ? selection.transition(maybeTransition) : selection;
        };
      };
      var containerTranslation = function containerTranslation(values) {
        return 'translate(' + values.origin[0] + ', ' + values.origin[1] + ')';
      };
      var boxPlot = function boxPlot(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        var transitionPropagator = propagateTransition(selection);
        selection.each(function (data, index, group) {
          var filteredData = data.filter(base.defined());
          var g = join(d3Selection.select(group[index]), filteredData);
          g.enter().attr('stroke', colors.black).attr('fill', colors.gray).attr('transform', function (d, i) {
            return containerTranslation(base.values(d, i)) + ' scale(1e-6, 1)';
          }).append('path');
          pathGenerator.orient(base.orient());
          g.each(function (d, i, g) {
            var values = base.values(d, i);
            pathGenerator.median(values.median).upperQuartile(values.upperQuartile).lowerQuartile(values.lowerQuartile).width(values.width).high(values.high).low(values.low);
            transitionPropagator(d3Selection.select(g[i])).attr('transform', containerTranslation(values)).select('path').attr('d', pathGenerator([d]));
          });
          base.decorate()(g, data, index);
        });
      };
      rebindAll(boxPlot, base);
      rebind(boxPlot, join, 'key');
      rebind(boxPlot, pathGenerator, 'cap');
      return boxPlot;
    });

    var boxPlot$1 = (function () {
      var base = boxPlotBase();
      var pathGenerator = shapeBoxPlot().value(0);
      var boxPlot = function boxPlot(data) {
        var filteredData = data.filter(base.defined());
        var context = pathGenerator.context();
        pathGenerator.orient(base.orient());
        filteredData.forEach(function (d, i) {
          context.save();
          var values = base.values(d, i);
          context.translate(values.origin[0], values.origin[1]);
          context.beginPath();
          context.fillStyle = colors.gray;
          context.strokeStyle = colors.black;
          base.decorate()(context, d, i);
          pathGenerator.median(values.median).upperQuartile(values.upperQuartile).lowerQuartile(values.lowerQuartile).high(values.high).width(values.width).low(values.low)([d]);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebindAll(boxPlot, base);
      rebind(boxPlot, pathGenerator, 'cap', 'context');
      return boxPlot;
    });

    var boxPlot = (function () {
      var base = boxPlotBase();
      var crossValueAttribute = webglAttribute();
      var highValueAttribute = webglAttribute();
      var upperQuartileValueAttribute = webglAttribute();
      var medianValueAttribute = webglAttribute();
      var lowerQuartileValueAttribute = webglAttribute();
      var lowValueAttribute = webglAttribute();
      var bandwidthAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var capAttribute = webglAttribute().type(types.UNSIGNED_SHORT);
      var definedAttribute = webglAttribute().type(types.UNSIGNED_BYTE);
      var draw = webglSeriesBoxPlot().crossValueAttribute(crossValueAttribute).highValueAttribute(highValueAttribute).upperQuartileValueAttribute(upperQuartileValueAttribute).medianValueAttribute(medianValueAttribute).lowerQuartileValueAttribute(lowerQuartileValueAttribute).lowValueAttribute(lowValueAttribute).bandwidthAttribute(bandwidthAttribute).capAttribute(capAttribute).definedAttribute(definedAttribute);
      var equals = function equals(previousData, data) {
        return false;
      };
      var scaleMapper = webglScaleMapper;
      var previousData = [];
      var previousXScale = null;
      var previousYScale = null;
      var cap = functor$2(20);
      var boxPlot = function boxPlot(data) {
        if (base.orient() !== 'vertical') {
          throw new Error("Unsupported orientation ".concat(base.orient()));
        }
        var xScale = scaleMapper(base.xScale());
        var yScale = scaleMapper(base.yScale());
        var dataChanged = !equals(previousData, data);
        if (dataChanged) {
          previousData = data;
          bandwidthAttribute.value(function (d, i) {
            return base.bandwidth()(d, i);
          }).data(data);
          capAttribute.value(function (d, i) {
            return cap(d, i);
          }).data(data);
          definedAttribute.value(function (d, i) {
            return base.defined()(d, i);
          }).data(data);
        }
        if (dataChanged || xScale.scale !== previousXScale) {
          previousXScale = xScale.scale;
          crossValueAttribute.value(function (d, i) {
            return xScale.scale(base.crossValue()(d, i));
          }).data(data);
        }
        if (dataChanged || yScale.scale !== previousYScale) {
          previousYScale = yScale.scale;
          highValueAttribute.value(function (d, i) {
            return yScale.scale(base.highValue()(d, i));
          }).data(data);
          upperQuartileValueAttribute.value(function (d, i) {
            return yScale.scale(base.upperQuartileValue()(d, i));
          }).data(data);
          medianValueAttribute.value(function (d, i) {
            return yScale.scale(base.medianValue()(d, i));
          }).data(data);
          lowerQuartileValueAttribute.value(function (d, i) {
            return yScale.scale(base.lowerQuartileValue()(d, i));
          }).data(data);
          lowValueAttribute.value(function (d, i) {
            return yScale.scale(base.lowValue()(d, i));
          }).data(data);
        }
        draw.xScale(xScale.webglScale).yScale(yScale.webglScale).decorate(function (program) {
          return base.decorate()(program, data, 0);
        });
        draw(data.length);
      };
      boxPlot.cap = function () {
        if (!arguments.length) {
          return cap;
        }
        cap = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return boxPlot;
      };
      boxPlot.equals = function () {
        if (!arguments.length) {
          return equals;
        }
        equals = arguments.length <= 0 ? undefined : arguments[0];
        return boxPlot;
      };
      boxPlot.scaleMapper = function () {
        if (!arguments.length) {
          return scaleMapper;
        }
        scaleMapper = arguments.length <= 0 ? undefined : arguments[0];
        return boxPlot;
      };
      rebindAll(boxPlot, base, exclude('align'));
      rebind(boxPlot, draw, 'context', 'lineWidth', 'pixelRatio');
      return boxPlot;
    });

    var ohlc$2 = (function () {
      return ohlcBase$2(shapeOhlc(), 'ohlc');
    });

    var ohlc$1 = (function () {
      return ohlcBase$1(shapeOhlc());
    });

    var ohlc = (function () {
      return ohlcBase(webglSeriesOhlc());
    });

    var multiBase = (function () {
      var series = [];
      var mapping = function mapping(d) {
        return d;
      };
      var key = function key(_, i) {
        return i;
      };
      var multi = createBase({
        decorate: function decorate() {},
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      multi.xValues = function () {
        return series.map(function (s) {
          return s.xValues();
        }).reduce(function (a, b) {
          return a.concat(b);
        });
      };
      multi.yValues = function () {
        return series.map(function (s) {
          return s.yValues();
        }).reduce(function (a, b) {
          return a.concat(b);
        });
      };
      multi.mapping = function () {
        if (!arguments.length) {
          return mapping;
        }
        mapping = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      multi.key = function () {
        if (!arguments.length) {
          return key;
        }
        key = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      multi.series = function () {
        if (!arguments.length) {
          return series;
        }
        series = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      return multi;
    });

    var seriesSvgMulti = (function () {
      var base = multiBase();
      var innerJoin = dataJoin('g');
      var join = dataJoin('g', 'multi');
      var multi = function multi(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
          innerJoin.transition(selection);
        }
        var mapping = base.mapping();
        var series = base.series();
        var xScale = base.xScale();
        var yScale = base.yScale();
        selection.each(function (data, index, group) {
          var container = join(d3Selection.select(group[index]), series);

          // iterate over the containers, 'call'-ing the series for each
          container.each(function (dataSeries, seriesIndex, seriesGroup) {
            dataSeries.xScale(xScale).yScale(yScale);
            var seriesData = mapping(data, seriesIndex, series);
            var innerContainer = innerJoin(d3Selection.select(seriesGroup[seriesIndex]), [seriesData]);
            innerContainer.call(dataSeries);
          });
          container.selection().order();
          base.decorate()(container, data, index);
        });
      };
      rebindAll(multi, base);
      rebind(multi, join, 'key');
      return multi;
    });

    var seriesCanvasMulti = (function () {
      var context = null;
      var base = multiBase();
      var multi = function multi(data) {
        var mapping = base.mapping();
        var series = base.series();
        var xScale = base.xScale();
        var yScale = base.yScale();
        series.forEach(function (dataSeries, index) {
          var seriesData = mapping(data, index, series);
          dataSeries.context(context).xScale(xScale).yScale(yScale);
          var adaptedDecorate;
          if (dataSeries.decorate) {
            adaptedDecorate = dataSeries.decorate();
            dataSeries.decorate(function (c, d, i) {
              base.decorate()(c, data, index);
              adaptedDecorate(c, d, i);
            });
          } else {
            base.decorate()(context, data, index);
          }
          dataSeries(seriesData);
          if (adaptedDecorate) {
            dataSeries.decorate(adaptedDecorate);
          }
        });
      };
      multi.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      rebindAll(multi, base);
      return multi;
    });

    var multiSeries = (function () {
      var context = null;
      var pixelRatio = 1;
      var base = multiBase();
      var multi = function multi(data) {
        var mapping = base.mapping();
        var series = base.series();
        var xScale = base.xScale();
        var yScale = base.yScale();
        series.forEach(function (dataSeries, index) {
          var seriesData = mapping(data, index, series);
          dataSeries.context(context).pixelRatio(pixelRatio).xScale(xScale).yScale(yScale);
          var adaptedDecorate;
          if (dataSeries.decorate) {
            adaptedDecorate = dataSeries.decorate();
            dataSeries.decorate(function (c, d, i) {
              base.decorate()(c, data, index);
              adaptedDecorate(c, d, i);
            });
          } else {
            base.decorate()(context, data, index);
          }
          dataSeries(seriesData);
          if (adaptedDecorate) {
            dataSeries.decorate(adaptedDecorate);
          }
        });
      };
      multi.context = function () {
        if (!arguments.length) {
          return context;
        }
        context = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      multi.pixelRatio = function () {
        if (!arguments.length) {
          return pixelRatio;
        }
        pixelRatio = arguments.length <= 0 ? undefined : arguments[0];
        return multi;
      };
      rebindAll(multi, base);
      return multi;
    });

    var groupedBase = (function (series) {
      var bandwidth = function bandwidth() {
        return 50;
      };
      var align = 'center';

      // the offset scale is used to offset each of the series within a group
      var offsetScale = d3Scale.scaleBand();
      var grouped = createBase({
        decorate: function decorate() {},
        xScale: d3Scale.scaleLinear(),
        yScale: d3Scale.scaleLinear()
      });

      // the bandwidth for the grouped series can be a function of datum / index. As a result
      // the offset scale required to cluster the 'sub' series is also dependent on datum / index.
      // This function computes the offset scale for a specific datum / index of the grouped series
      grouped.offsetScaleForDatum = function (data, d, i) {
        var width = bandwidth(d, i);
        var offset = alignOffset(align, width);
        var halfWidth = width / 2;
        return offsetScale.domain(d3Array.range(0, data.length)).range([-halfWidth + offset, halfWidth + offset]);
      };
      grouped.bandwidth = function () {
        if (!arguments.length) {
          return bandwidth;
        }
        bandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return grouped;
      };
      grouped.align = function () {
        if (!arguments.length) {
          return align;
        }
        align = arguments.length <= 0 ? undefined : arguments[0];
        return grouped;
      };
      rebindAll(grouped, offsetScale, includeMap({
        'paddingInner': 'paddingOuter'
      }));
      return grouped;
    });

    var grouped$1 = (function (series) {
      var base = groupedBase();
      var join = dataJoin('g', 'grouped');
      var grouped = function grouped(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        selection.each(function (data, index, group) {
          var g = join(d3Selection.select(group[index]), data);
          g.enter().append('g');
          g.select('g').each(function (_, index, group) {
            var container = d3Selection.select(group[index]);

            // create a composite scale that applies the required offset
            var isVertical = series.orient() !== 'horizontal';
            var compositeScale = function compositeScale(d, i) {
              var offset = base.offsetScaleForDatum(data, d, i);
              var baseScale = isVertical ? base.xScale() : base.yScale();
              return baseScale(d) + offset(index) + offset.bandwidth() / 2;
            };
            if (isVertical) {
              series.xScale(compositeScale);
              series.yScale(base.yScale());
            } else {
              series.yScale(compositeScale);
              series.xScale(base.xScale());
            }

            // if the sub-series has a bandwidth, set this from the offset scale
            if (series.bandwidth) {
              series.bandwidth(function (d, i) {
                return base.offsetScaleForDatum(data, d, i).bandwidth();
              });
            }

            // adapt the decorate function to give each series the correct index
            series.decorate(function (s, d) {
              return base.decorate()(s, d, index);
            });
            container.call(series);
          });
        });
      };
      rebindAll(grouped, series, exclude('decorate', 'xScale', 'yScale'));
      rebindAll(grouped, base, exclude('offsetScaleForDatum'));
      return grouped;
    });

    function grouped (series) {
      var base = groupedBase();
      var grouped = function grouped(data) {
        data.forEach(function (seriesData, index) {
          // create a composite scale that applies the required offset
          var isVertical = series.orient() !== 'horizontal';
          var compositeScale = function compositeScale(d, i) {
            var offset = base.offsetScaleForDatum(data, d, i);
            var baseScale = isVertical ? base.xScale() : base.yScale();
            return baseScale(d) + offset(index) + offset.bandwidth() / 2;
          };
          if (isVertical) {
            series.xScale(compositeScale);
            series.yScale(base.yScale());
          } else {
            series.yScale(compositeScale);
            series.xScale(base.xScale());
          }

          // if the sub-series has a bandwidth, set this from the offset scale
          if (series.bandwidth) {
            series.bandwidth(function (d, i) {
              return base.offsetScaleForDatum(data, d, i).bandwidth();
            });
          }

          // adapt the decorate function to give each series the correct index
          series.decorate(function (c, d) {
            return base.decorate()(c, d, index);
          });
          series(seriesData);
        });
      };
      rebindAll(grouped, series, exclude('decorate', 'xScale', 'yScale'));
      rebindAll(grouped, base, exclude('offsetScaleForDatum'));
      return grouped;
    }

    var repeat$2 = (function () {
      var orient = 'vertical';
      var series = seriesSvgLine();
      var multi = seriesSvgMulti();
      var repeat = function repeat(selection) {
        return selection.each(function (data, index, group) {
          if (orient === 'vertical') {
            multi.series(data[0].map(function (_) {
              return series;
            })).mapping(function (data, index) {
              return data.map(function (d) {
                return d[index];
              });
            });
          } else {
            multi.series(data.map(function (_) {
              return series;
            })).mapping(function (data, index) {
              return data[index];
            });
          }
          d3Selection.select(group[index]).call(multi);
        });
      };
      repeat.series = function () {
        if (!arguments.length) {
          return series;
        }
        series = arguments.length <= 0 ? undefined : arguments[0];
        return repeat;
      };
      repeat.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return repeat;
      };
      rebindAll(repeat, multi, exclude('series', 'mapping'));
      return repeat;
    });

    var repeat$1 = (function () {
      var orient = 'vertical';
      var series = seriesCanvasLine();
      var multi = seriesCanvasMulti();
      var repeat = function repeat(data) {
        if (orient === 'vertical') {
          multi.series(data[0].map(function (_) {
            return series;
          })).mapping(function (data, index) {
            return data.map(function (d) {
              return d[index];
            });
          });
        } else {
          multi.series(data.map(function (_) {
            return series;
          })).mapping(function (data, index) {
            return data[index];
          });
        }
        multi(data);
      };
      repeat.series = function () {
        if (!arguments.length) {
          return series;
        }
        series = arguments.length <= 0 ? undefined : arguments[0];
        return repeat;
      };
      repeat.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return repeat;
      };
      rebindAll(repeat, multi, exclude('series', 'mapping'));
      return repeat;
    });

    var repeat = (function () {
      var orient = 'vertical';
      var series = function series() {
        return line();
      };
      var multi = multiSeries();
      var seriesCache = [];
      var repeat = function repeat(data) {
        if (orient === 'vertical') {
          var previousSeriesCache = seriesCache;
          seriesCache = data[0].map(function (d, i) {
            return i < previousSeriesCache.length ? previousSeriesCache[i] : series();
          });
          multi.series(seriesCache).mapping(function (data, index) {
            return data.map(function (d) {
              return d[index];
            });
          });
        } else {
          var _previousSeriesCache = seriesCache;
          seriesCache = data.map(function (d, i) {
            return i < _previousSeriesCache.length ? _previousSeriesCache[i] : series();
          });
          multi.series(seriesCache).mapping(function (data, index) {
            return data[index];
          });
        }
        multi(data);
      };
      repeat.series = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        if (!args.length) {
          return series;
        }
        if (typeof args[0].xScale === 'function' && typeof args[0].yScale === 'function') {
          series = function series() {
            return args[0];
          };
        } else {
          series = args[0];
        }
        seriesCache = [];
        return repeat;
      };
      repeat.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        seriesCache = [];
        return repeat;
      };
      rebindAll(repeat, multi, exclude('series', 'mapping'));
      return repeat;
    });

    var sortUnique = function sortUnique(arr) {
      return arr.sort(d3Array.ascending).filter(function (value, index, self) {
        return self.indexOf(value, index + 1) === -1;
      });
    };
    var autoBandwidth = (function (adaptee) {
      var widthFraction = 0.75;

      // computes the bandwidth as a fraction of the smallest distance between the datapoints
      var computeBandwidth = function computeBandwidth(screenValues) {
        // return some default value if there are not enough datapoints to compute the width
        if (screenValues.length <= 1) {
          return 10;
        }
        screenValues = sortUnique(screenValues);

        // compute the distance between neighbouring items
        var neighbourDistances = d3Array.pairs(screenValues).map(function (tuple) {
          return Math.abs(tuple[0] - tuple[1]);
        });
        var minDistance = d3Array.min(neighbourDistances);
        return widthFraction * minDistance;
      };
      var determineBandwith = function determineBandwith(crossScale, data, accessor) {
        // if the cross-scale has a bandwidth function, i.e. it is a scaleBand, use
        // this to determine the width
        if (crossScale.bandwidth) {
          return crossScale.bandwidth();
        } else {
          var _ref;
          // grouped series expect a nested array, which is flattened out
          var flattenedData = Array.isArray(data) ? (_ref = []).concat.apply(_ref, _toConsumableArray(data)) : data;

          // obtain an array of points along the crossValue axis, mapped to screen coordinates.
          var crossValuePoints = flattenedData.filter(adaptee.defined()).map(accessor()).map(crossScale);
          var width = computeBandwidth(crossValuePoints);
          return width;
        }
      };
      var autoBandwidth = function autoBandwidth(arg) {
        var computeWidth = function computeWidth(data) {
          if (adaptee.xBandwidth && adaptee.yBandwidth) {
            adaptee.xBandwidth(determineBandwith(adaptee.xScale(), data, adaptee.xValue));
            adaptee.yBandwidth(determineBandwith(adaptee.yScale(), data, adaptee.yValue));
          } else {
            // if the series has an orient property, use this to determine the cross-scale, otherwise
            // assume it is the x-scale
            var crossScale = adaptee.orient && adaptee.orient() === 'horizontal' ? adaptee.yScale() : adaptee.xScale();
            adaptee.bandwidth(determineBandwith(crossScale, data, adaptee.crossValue));
          }
        };
        if (arg instanceof d3Selection.selection) {
          arg.each(function (data, index, group) {
            computeWidth(data);
            adaptee(d3Selection.select(group[index]));
          });
        } else {
          computeWidth(arg);
          adaptee(arg);
        }
      };
      rebindAll(autoBandwidth, adaptee);
      autoBandwidth.widthFraction = function () {
        if (!arguments.length) {
          return widthFraction;
        }
        widthFraction = arguments.length <= 0 ? undefined : arguments[0];
        return autoBandwidth;
      };
      return autoBandwidth;
    });

    var heatmapBase = (function () {
      var xValue = function xValue(d) {
        return d.x;
      };
      var yValue = function yValue(d) {
        return d.y;
      };
      var colorValue = function colorValue(d) {
        return d.color;
      };
      var yBandwidth = function yBandwidth() {
        return 5;
      };
      var xBandwidth = function xBandwidth() {
        return 5;
      };
      var colorInterpolate = d3ScaleChromatic.interpolateViridis;
      var heatmap = createBase({
        decorate: function decorate() {},
        defined: function defined$1(d, i) {
          return defined(xValue, yValue, colorValue)(d, i);
        },
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity()
      });
      heatmap.pathGenerator = shapeBar().x(0).y(0);
      heatmap.colorScale = function (data) {
        var colorValues = data.map(colorValue);
        // a scale that maps the color values onto a unit range, [0, 1]
        return d3Scale.scaleLinear().domain([d3Array.min(colorValues), d3Array.max(colorValues)]);
      };
      heatmap.values = function (d, i) {
        return {
          x: heatmap.xScale()(xValue(d, i)),
          y: heatmap.yScale()(yValue(d, i)),
          colorValue: colorValue(d, i),
          width: xBandwidth(d, i),
          height: yBandwidth(d, i)
        };
      };
      heatmap.xValues = function () {
        return [xValue];
      };
      heatmap.yValues = function () {
        return [yValue];
      };
      heatmap.xValue = function () {
        if (!arguments.length) {
          return xValue;
        }
        xValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return heatmap;
      };
      heatmap.yValue = function () {
        if (!arguments.length) {
          return yValue;
        }
        yValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return heatmap;
      };
      heatmap.colorValue = function () {
        if (!arguments.length) {
          return colorValue;
        }
        colorValue = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return heatmap;
      };
      heatmap.colorInterpolate = function () {
        if (!arguments.length) {
          return colorInterpolate;
        }
        colorInterpolate = arguments.length <= 0 ? undefined : arguments[0];
        return heatmap;
      };
      heatmap.xBandwidth = function () {
        if (!arguments.length) {
          return xBandwidth;
        }
        xBandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return heatmap;
      };
      heatmap.yBandwidth = function () {
        if (!arguments.length) {
          return yBandwidth;
        }
        yBandwidth = functor$2(arguments.length <= 0 ? undefined : arguments[0]);
        return heatmap;
      };
      rebindAll(heatmap, heatmap.pathGenerator, includeMap({
        'horizontalAlign': 'xAlign',
        'verticalAlign': 'yAlign'
      }));
      return heatmap;
    });

    var heatmap$1 = (function () {
      var base = heatmapBase();
      var join = dataJoin('g', 'box');
      var containerTransform = function containerTransform(values) {
        return 'translate(' + values.x + ', ' + values.y + ')';
      };
      var heatmap = function heatmap(selection) {
        selection.each(function (data, index, group) {
          var filteredData = data.filter(base.defined());
          var colorValue = base.colorValue();
          var colorInterpolate = base.colorInterpolate();
          var colorScale = base.colorScale(filteredData);
          var g = join(d3Selection.select(group[index]), filteredData);
          g.enter().append('path').attr('stroke', 'transparent');
          g.attr('transform', function (d, i) {
            return containerTransform(base.values(d, i));
          }).select('path').attr('d', function (d, i) {
            return base.pathGenerator.width(base.values(d, i).width).height(base.values(d, i).height)([d]);
          }).attr('fill', function (d, i) {
            return colorInterpolate(colorScale(colorValue(d, i)));
          });
          base.decorate()(g, data, index);
        });
      };
      rebindAll(heatmap, base);
      return heatmap;
    });

    var heatmap = (function () {
      var base = heatmapBase();
      var heatmap = function heatmap(data) {
        var filteredData = data.filter(base.defined());
        var colorInterpolate = base.colorInterpolate();
        var colorScale = base.colorScale(filteredData);
        var context = base.pathGenerator.context();
        filteredData.forEach(function (d, i) {
          context.save();
          context.beginPath();
          var values = base.values(d, i);
          context.translate(values.x, values.y);
          context.fillStyle = colorInterpolate(colorScale(values.colorValue));
          context.strokeStyle = 'transparent';
          base.decorate()(context, d, i);
          base.pathGenerator.height(values.height).width(values.width)([d]);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      rebind(heatmap, base.pathGenerator, 'context');
      rebindAll(heatmap, base);
      return heatmap;
    });

    var constant = (function (value) {
      return typeof value === 'function' ? value : function () {
        return value;
      };
    });

    var band$1 = (function () {
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var orient = 'horizontal';
      var fromValue = function fromValue(d) {
        return d.from;
      };
      var toValue = function toValue(d) {
        return d.to;
      };
      var decorate = function decorate() {};
      var join = dataJoin('g', 'annotation-band');
      var pathGenerator = shapeBar().horizontalAlign('center').verticalAlign('center').x(0).y(0);
      var instance = function instance(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        if (orient !== 'horizontal' && orient !== 'vertical') {
          throw new Error('Invalid orientation');
        }
        var horizontal = orient === 'horizontal';
        var translation = horizontal ? function (a, b) {
          return "translate(".concat(a, ", ").concat(b, ")");
        } : function (a, b) {
          return "translate(".concat(b, ", ").concat(a, ")");
        };
        // the value scale which the annotation 'value' relates to, the crossScale
        // is the other. Which is which depends on the orienation!
        var crossScale = horizontal ? xScale : yScale;
        var valueScale = horizontal ? yScale : xScale;
        var crossScaleRange = crossScale.range();
        var crossScaleSize = crossScaleRange[1] - crossScaleRange[0];
        var valueAxisDimension = horizontal ? 'height' : 'width';
        var crossAxisDimension = horizontal ? 'width' : 'height';
        var containerTransform = function containerTransform() {
          return translation((crossScaleRange[1] + crossScaleRange[0]) / 2, (valueScale(toValue.apply(void 0, arguments)) + valueScale(fromValue.apply(void 0, arguments))) / 2);
        };
        pathGenerator[crossAxisDimension](crossScaleSize);
        pathGenerator[valueAxisDimension](function () {
          return valueScale(toValue.apply(void 0, arguments)) - valueScale(fromValue.apply(void 0, arguments));
        });
        selection.each(function (data, index, nodes) {
          var g = join(d3Selection.select(nodes[index]), data);
          g.enter().attr('transform', containerTransform).append('path').classed('band', true);
          g.attr('class', "annotation-band ".concat(orient)).attr('transform', containerTransform).select('path')
          // the path generator is being used to render a single path, hence
          // an explicit index is provided
          .attr('d', function (d, i) {
            return pathGenerator([d], i);
          });
          decorate(g, data, index);
        });
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.fromValue = function () {
        if (!arguments.length) {
          return fromValue;
        }
        fromValue = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.toValue = function () {
        if (!arguments.length) {
          return toValue;
        }
        toValue = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      return instance;
    });

    var band = (function () {
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var orient = 'horizontal';
      var fromValue = function fromValue(d) {
        return d.from;
      };
      var toValue = function toValue(d) {
        return d.to;
      };
      var decorate = function decorate() {};
      var pathGenerator = shapeBar().horizontalAlign('right').verticalAlign('top');
      var instance = function instance(data) {
        if (orient !== 'horizontal' && orient !== 'vertical') {
          throw new Error('Invalid orientation');
        }
        var context = pathGenerator.context();
        var horizontal = orient === 'horizontal';
        // the value scale which the annotation 'value' relates to, the crossScale
        // is the other. Which is which depends on the orienation!
        var crossScale = horizontal ? xScale : yScale;
        var valueScale = horizontal ? yScale : xScale;
        var crossScaleRange = crossScale.range();
        var crossScaleSize = crossScaleRange[1] - crossScaleRange[0];
        var valueAxisStart = horizontal ? 'x' : 'y';
        var crossAxisStart = horizontal ? 'y' : 'x';
        var valueAxisDimension = horizontal ? 'height' : 'width';
        var crossAxisDimension = horizontal ? 'width' : 'height';
        data.forEach(function (d, i) {
          context.save();
          context.beginPath();
          context.strokeStyle = 'transparent';
          pathGenerator[crossAxisStart](valueScale(fromValue(d)));
          pathGenerator[valueAxisStart](crossScaleRange[0]);
          pathGenerator[crossAxisDimension](crossScaleSize);
          pathGenerator[valueAxisDimension](valueScale(toValue(d)) - valueScale(fromValue(d)));
          decorate(context, d, i);
          pathGenerator.context(context)([d], i);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.fromValue = function () {
        if (!arguments.length) {
          return fromValue;
        }
        fromValue = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.toValue = function () {
        if (!arguments.length) {
          return toValue;
        }
        toValue = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      rebind(instance, pathGenerator, 'context');
      return instance;
    });

    var annotationLine$1 = (function () {
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var value = function value(d) {
        return d;
      };
      var label = value;
      var decorate = function decorate() {};
      var orient = 'horizontal';
      var join = dataJoin('g', 'annotation-line');
      var instance = function instance(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        if (orient !== 'horizontal' && orient !== 'vertical') {
          throw new Error('Invalid orientation');
        }
        var horizontal = orient === 'horizontal';
        var translation = horizontal ? function (a, b) {
          return "translate(".concat(a, ", ").concat(b, ")");
        } : function (a, b) {
          return "translate(".concat(b, ", ").concat(a, ")");
        };
        var lineProperty = horizontal ? 'x2' : 'y2';
        // the value scale which the annotation 'value' relates to, the crossScale
        // is the other. Which is which depends on the orienation!
        var crossScale = horizontal ? xScale : yScale;
        var valueScale = horizontal ? yScale : xScale;
        var handleOne = horizontal ? 'left-handle' : 'bottom-handle';
        var handleTwo = horizontal ? 'right-handle' : 'top-handle';
        var textOffsetX = horizontal ? '9' : '0';
        var textOffsetY = horizontal ? '0' : '9';
        var textOffsetDeltaY = horizontal ? '0.32em' : '0.71em';
        var textAnchor = horizontal ? 'start' : 'middle';
        var scaleRange = crossScale.range();
        // the transform that sets the 'origin' of the annotation
        var containerTransform = function containerTransform() {
          return translation(scaleRange[0], valueScale(value.apply(void 0, arguments)));
        };
        var scaleWidth = scaleRange[1] - scaleRange[0];
        selection.each(function (data, selectionIndex, nodes) {
          var g = join(d3Selection.select(nodes[selectionIndex]), data);

          // create the outer container and line
          var enter = g.enter().attr('transform', containerTransform).style('stroke', '#bbb');
          enter.append('line').attr(lineProperty, scaleWidth);

          // create containers at each end of the annotation
          enter.append('g').classed(handleOne, true).style('stroke', 'none');
          enter.append('g').classed(handleTwo, true).style('stroke', 'none').attr('transform', translation(scaleWidth, 0)).append('text').attr('text-anchor', textAnchor).attr('x', textOffsetX).attr('y', textOffsetY).attr('dy', textOffsetDeltaY);

          // Update
          g.attr('class', "annotation-line ".concat(orient));

          // translate the parent container to the left hand edge of the annotation
          g.attr('transform', containerTransform);

          // update the elements that depend on scale width
          g.select('line').attr(lineProperty, scaleWidth);
          g.select('g.' + handleTwo).attr('transform', translation(scaleWidth, 0));

          // Update the text label
          g.select('text').text(label);
          decorate(g, data, selectionIndex);
        });
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.label = function () {
        if (!arguments.length) {
          return label;
        }
        label = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      return instance;
    });

    function crosshair$1 () {
      var x = function x(d) {
        return d.x;
      };
      var y = function y(d) {
        return d.y;
      };
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var decorate = function decorate() {};
      var join = dataJoin('g', 'annotation-crosshair');
      var point = seriesSvgPoint();
      var horizontalLine = annotationLine$1();
      var verticalLine = annotationLine$1().orient('vertical');

      // The line annotations and point series used to render the crosshair are positioned using
      // screen coordinates. This function constructs an identity scale for these components.
      var xIdentity = d3Scale.scaleIdentity();
      var yIdentity = d3Scale.scaleIdentity();
      var multi = seriesSvgMulti().series([horizontalLine, verticalLine, point]).xScale(xIdentity).yScale(yIdentity).mapping(function (data) {
        return [data];
      });
      var instance = function instance(selection) {
        if (isTransition(selection)) {
          join.transition(selection);
        }
        selection.each(function (data, index, nodes) {
          var g = join(d3Selection.select(nodes[index]), data);

          // Prevent the crosshair triggering pointer events on itself
          g.enter().style('pointer-events', 'none');

          // Assign the identity scales an accurate range to allow the line annotations to cover
          // the full width/height of the chart.
          xIdentity.range(xScale.range());
          yIdentity.range(yScale.range());
          point.crossValue(x).mainValue(y);
          horizontalLine.value(y);
          verticalLine.value(x);
          g.call(multi);
          decorate(g, data, index);
        });
      };

      // Don't use the xValue/yValue convention to indicate that these values are in screen
      // not domain co-ordinates and are therefore not scaled.
      instance.x = function () {
        if (!arguments.length) {
          return x;
        }
        x = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.y = function () {
        if (!arguments.length) {
          return y;
        }
        y = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      var lineIncludes = include('label');
      rebindAll(instance, horizontalLine, lineIncludes, prefix('y'));
      rebindAll(instance, verticalLine, lineIncludes, prefix('x'));
      return instance;
    }

    var annotationLine = (function () {
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var value = function value(d) {
        return d;
      };
      var label = value;
      var decorate = function decorate() {};
      var orient = 'horizontal';
      var lineData = d3Shape.line();
      var instance = function instance(data) {
        if (orient !== 'horizontal' && orient !== 'vertical') {
          throw new Error('Invalid orientation');
        }
        var horizontal = orient === 'horizontal';
        var context = lineData.context();
        // the value scale which the annotation 'value' relates to, the crossScale
        // is the other. Which is which depends on the orienation!
        var crossScale = horizontal ? xScale : yScale;
        var valueScale = horizontal ? yScale : xScale;
        var crossDomain = crossScale.domain();
        var textOffsetX = horizontal ? 9 : 0;
        var textOffsetY = horizontal ? 0 : 9;
        var textAlign = horizontal ? 'left' : 'center';
        var textBaseline = horizontal ? 'middle' : 'hanging';
        data.forEach(function (d, i) {
          context.save();
          context.beginPath();
          context.strokeStyle = '#bbb';
          context.fillStyle = '#000';
          context.textAlign = textAlign;
          context.textBaseline = textBaseline;
          decorate(context, d, i);

          // Draw line
          lineData.context(context)(crossDomain.map(function (extent) {
            var point = [crossScale(extent), valueScale(value(d))];
            return horizontal ? point : point.reverse();
          }));

          // Draw label
          var x = horizontal ? crossScale(crossDomain[1]) : valueScale(value(d));
          var y = horizontal ? valueScale(value(d)) : crossScale(crossDomain[1]);
          context.fillText(label(d), x + textOffsetX, y + textOffsetY);
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.label = function () {
        if (!arguments.length) {
          return label;
        }
        label = constant(arguments.length <= 0 ? undefined : arguments[0]);
        return instance;
      };
      instance.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      rebind(instance, lineData, 'context');
      return instance;
    });

    var crosshair = (function () {
      var x = function x(d) {
        return d.x;
      };
      var y = function y(d) {
        return d.y;
      };
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var point = seriesCanvasPoint();
      var horizontalLine = annotationLine();
      var verticalLine = annotationLine().orient('vertical');

      // The line annotations and point series used to render the crosshair are positioned using
      // screen coordinates. This function constructs an identity scale for these components.
      var xIdentity = d3Scale.scaleIdentity();
      var yIdentity = d3Scale.scaleIdentity();
      var multi = seriesCanvasMulti().series([horizontalLine, verticalLine, point]).xScale(xIdentity).yScale(yIdentity).mapping(function (data) {
        return [data];
      });
      var instance = function instance(data) {
        data.forEach(function (d) {
          // Assign the identity scales an accurate range to allow the line annotations to cover
          // the full width/height of the chart.
          xIdentity.range(xScale.range());
          yIdentity.range(yScale.range());
          point.crossValue(x).mainValue(y);
          horizontalLine.value(y);
          verticalLine.value(x);
          multi(d);
        });
      };

      // Don't use the xValue/yValue convention to indicate that these values are in screen
      // not domain co-ordinates and are therefore not scaled.
      instance.x = function () {
        if (!arguments.length) {
          return x;
        }
        x = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.y = function () {
        if (!arguments.length) {
          return y;
        }
        y = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      var lineIncludes = include('label', 'decorate');
      rebindAll(instance, horizontalLine, lineIncludes, prefix('y'));
      rebindAll(instance, verticalLine, lineIncludes, prefix('x'));
      rebind(instance, point, 'decorate');
      rebind(instance, multi, 'context');
      return instance;
    });

    var ticks = (function () {
      var scale = d3Scale.scaleIdentity();
      var tickArguments = [10];
      var tickValues = null;
      var ticks = function ticks() {
        var _scale;
        return tickValues != null ? tickValues : scale.ticks ? (_scale = scale).ticks.apply(_scale, _toConsumableArray(tickArguments)) : scale.domain();
      };
      ticks.scale = function () {
        if (!arguments.length) {
          return scale;
        }
        scale = arguments.length <= 0 ? undefined : arguments[0];
        return ticks;
      };
      ticks.ticks = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        tickArguments = args;
        return ticks;
      };
      ticks.tickArguments = function () {
        if (!arguments.length) {
          return tickArguments;
        }
        tickArguments = arguments.length <= 0 ? undefined : arguments[0];
        return ticks;
      };
      ticks.tickValues = function () {
        if (!arguments.length) {
          return tickValues;
        }
        tickValues = arguments.length <= 0 ? undefined : arguments[0];
        return ticks;
      };
      return ticks;
    });

    var identity$2 = function identity(d) {
      return d;
    };
    var gridline$1 = (function () {
      var xDecorate = function xDecorate() {};
      var yDecorate = function yDecorate() {};
      var xTicks = ticks();
      var yTicks = ticks();
      var xJoin = dataJoin('line', 'gridline-y').key(identity$2);
      var yJoin = dataJoin('line', 'gridline-x').key(identity$2);
      var instance = function instance(selection) {
        if (isTransition(selection)) {
          xJoin.transition(selection);
          yJoin.transition(selection);
        }
        selection.each(function (data, index, nodes) {
          var element = nodes[index];
          var container = d3Selection.select(nodes[index]);
          var xScale = xTicks.scale();
          var yScale = yTicks.scale();

          // Stash a snapshot of the scale, and retrieve the old snapshot.
          var xScaleOld = element.__x_scale__ || xScale;
          element.__x_scale__ = xScale.copy();
          var xData = xTicks();
          var xLines = xJoin(container, xData);
          xLines.enter().attr('x1', xScaleOld).attr('x2', xScaleOld).attr('y1', yScale.range()[0]).attr('y2', yScale.range()[1]).attr('stroke', '#bbb');
          xLines.attr('x1', xScale).attr('x2', xScale).attr('y1', yScale.range()[0]).attr('y2', yScale.range()[1]);
          xLines.exit().attr('x1', xScale).attr('x2', xScale);
          xDecorate(xLines, xData, index);

          // Stash a snapshot of the scale, and retrieve the old snapshot.
          var yScaleOld = element.__y_scale__ || yScale;
          element.__y_scale__ = yScale.copy();
          var yData = yTicks();
          var yLines = yJoin(container, yData);
          yLines.enter().attr('y1', yScaleOld).attr('y2', yScaleOld).attr('x1', xScale.range()[0]).attr('x2', xScale.range()[1]).attr('stroke', '#bbb');
          yLines.attr('y1', yScale).attr('y2', yScale).attr('x1', xScale.range()[0]).attr('x2', xScale.range()[1]);
          yLines.exit().attr('y1', yScale).attr('y2', yScale);
          yDecorate(yLines, yData, index);
        });
      };
      instance.yDecorate = function () {
        if (!arguments.length) {
          return yDecorate;
        }
        yDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.xDecorate = function () {
        if (!arguments.length) {
          return xDecorate;
        }
        xDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      rebindAll(instance, xJoin, includeMap({
        'key': 'xKey'
      }));
      rebindAll(instance, yJoin, includeMap({
        'key': 'yKey'
      }));
      rebindAll(instance, xTicks, prefix('x'));
      rebindAll(instance, yTicks, prefix('y'));
      return instance;
    });

    var gridline = (function () {
      var xDecorate = function xDecorate() {};
      var yDecorate = function yDecorate() {};
      var xTicks = ticks();
      var yTicks = ticks();
      var lineData = d3Shape.line();
      var instance = function instance() {
        var context = lineData.context();
        var xScale = xTicks.scale();
        var yScale = yTicks.scale();
        xTicks().forEach(function (xTick, i) {
          context.save();
          context.beginPath();
          context.strokeStyle = '#bbb';
          context.fillStyle = 'transparent';
          xDecorate(context, xTick, i);
          lineData.context(context)(yScale.domain().map(function (d) {
            return [xScale(xTick), yScale(d)];
          }));
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
        yTicks().forEach(function (yTick, i) {
          context.save();
          context.beginPath();
          context.strokeStyle = '#bbb';
          context.fillStyle = 'transparent';
          yDecorate(context, yTick, i);
          lineData.context(context)(xScale.domain().map(function (d) {
            return [xScale(d), yScale(yTick)];
          }));
          context.fill();
          context.stroke();
          context.closePath();
          context.restore();
        });
      };
      instance.yDecorate = function () {
        if (!arguments.length) {
          return yDecorate;
        }
        yDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      instance.xDecorate = function () {
        if (!arguments.length) {
          return xDecorate;
        }
        xDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return instance;
      };
      rebindAll(instance, xTicks, prefix('x'));
      rebindAll(instance, yTicks, prefix('y'));
      rebind(instance, lineData, 'context');
      return instance;
    });

    // these utilities capture some of the relatively complex logic within d3-axis which 
    // determines the ticks and tick formatter based on various axis and scale
    // properties: https://github.com/d3/d3-axis#axis_ticks 

    var identity$1 = function identity(d) {
      return d;
    };
    var tryApply = function tryApply(scale, fn, args, defaultVal) {
      return scale[fn] ? scale[fn].apply(scale, args) : defaultVal;
    };
    var ticksArrayForAxis = function ticksArrayForAxis(axis) {
      var _axis$tickValues;
      return (_axis$tickValues = axis.tickValues()) !== null && _axis$tickValues !== void 0 ? _axis$tickValues : tryApply(axis.scale(), 'ticks', axis.tickArguments(), axis.scale().domain());
    };
    var tickFormatterForAxis = function tickFormatterForAxis(axis) {
      var _axis$tickFormat;
      return (_axis$tickFormat = axis.tickFormat()) !== null && _axis$tickFormat !== void 0 ? _axis$tickFormat : tryApply(axis.scale(), 'tickFormat', axis.tickArguments(), identity$1);
    };

    var identity = function identity(d) {
      return d;
    };
    var axisBase = function axisBase(orient, scale) {
      var custom = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};
      var tickArguments = [10];
      var tickValues = null;
      var decorate = function decorate() {};
      var tickFormat = null;
      var tickSizeOuter = 6;
      var tickSizeInner = 6;
      var tickPadding = 3;
      var svgDomainLine = d3Shape.line();
      var dataJoin$1 = dataJoin('g', 'tick').key(identity);
      var domainPathDataJoin = dataJoin('path', 'domain');
      var defaultLabelOffset = function defaultLabelOffset() {
        return {
          offset: [0, tickSizeInner + tickPadding]
        };
      };
      var defaultTickPath = function defaultTickPath() {
        return {
          path: [[0, 0], [0, tickSizeInner]]
        };
      };
      var labelOffset = custom.labelOffset || defaultLabelOffset;
      var tickPath = custom.tickPath || defaultTickPath;

      // returns a function that creates a translation based on
      // the bound data
      var containerTranslate = function containerTranslate(scale, trans) {
        var offset = 0;
        if (scale.bandwidth) {
          offset = scale.bandwidth() / 2;
          if (scale.round()) {
            offset = Math.round(offset);
          }
        }
        return function (d) {
          return trans(scale(d) + offset, 0);
        };
      };
      var translate = function translate(x, y) {
        return isVertical() ? "translate(".concat(y, ", ").concat(x, ")") : "translate(".concat(x, ", ").concat(y, ")");
      };
      var pathTranspose = function pathTranspose(arr) {
        return isVertical() ? arr.map(function (d) {
          return [d[1], d[0]];
        }) : arr;
      };
      var isVertical = function isVertical() {
        return orient === 'left' || orient === 'right';
      };
      var axis = function axis(selection) {
        if (isTransition(selection)) {
          dataJoin$1.transition(selection);
          domainPathDataJoin.transition(selection);
        }
        selection.each(function (data, index, group) {
          var element = group[index];
          var container = d3Selection.select(element);
          if (!element.__scale__) {
            container.attr('fill', 'none').attr('font-size', 10).attr('font-family', 'sans-serif').attr('text-anchor', orient === 'right' ? 'start' : orient === 'left' ? 'end' : 'middle');
          }

          // Stash a snapshot of the new scale, and retrieve the old snapshot.
          var scaleOld = element.__scale__ || scale;
          element.__scale__ = scale.copy();
          var ticksArray = ticksArrayForAxis(axis);
          var tickFormatter = tickFormatterForAxis(axis);
          var sign = orient === 'bottom' || orient === 'right' ? 1 : -1;
          var withSign = function withSign(_ref) {
            var _ref2 = _slicedToArray(_ref, 2),
              x = _ref2[0],
              y = _ref2[1];
            return [x, sign * y];
          };

          // add the domain line
          var range = scale.range();
          var domainPathData = pathTranspose([[range[0], sign * tickSizeOuter], [range[0], 0], [range[1], 0], [range[1], sign * tickSizeOuter]]);
          var domainLine = domainPathDataJoin(container, [data]);
          domainLine.enter().attr('stroke', '#000');
          domainLine.attr('d', svgDomainLine(domainPathData));
          var g = dataJoin$1(container, ticksArray);
          var labelOffsets = ticksArray.map(function (d, i) {
            return labelOffset(d, i, ticksArray);
          });
          var tickPaths = ticksArray.map(function (d, i) {
            return tickPath(d, i, ticksArray);
          });

          // enter
          g.enter().attr('transform', containerTranslate(scaleOld, translate)).append('path').attr('stroke', '#000');
          g.enter().append('text').attr('transform', function (d, i) {
            return translate.apply(void 0, _toConsumableArray(withSign(labelOffsets[i].offset)));
          }).attr('fill', '#000');

          // exit
          g.exit().attr('transform', containerTranslate(scale, translate));

          // update
          g.select('path').attr('visibility', function (d, i) {
            return tickPaths[i].hidden && 'hidden';
          }).attr('d', function (d, i) {
            return svgDomainLine(pathTranspose(tickPaths[i].path.map(withSign)));
          });
          g.select('text').attr('visibility', function (d, i) {
            return labelOffsets[i].hidden && 'hidden';
          }).attr('transform', function (d, i) {
            return translate.apply(void 0, _toConsumableArray(withSign(labelOffsets[i].offset)));
          }).attr('dy', function () {
            var offset = '0em';
            if (isVertical()) {
              offset = '0.32em';
            } else if (orient === 'bottom') {
              offset = '0.71em';
            }
            return offset;
          }).text(tickFormatter);
          g.attr('transform', containerTranslate(scale, translate));
          decorate(g, data, index);
        });
      };
      axis.tickFormat = function () {
        if (!arguments.length) {
          return tickFormat;
        }
        tickFormat = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      axis.tickSize = function () {
        if (!arguments.length) {
          return tickSizeInner;
        }
        tickSizeInner = tickSizeOuter = Number(arguments.length <= 0 ? undefined : arguments[0]);
        return axis;
      };
      axis.tickSizeInner = function () {
        if (!arguments.length) {
          return tickSizeInner;
        }
        tickSizeInner = Number(arguments.length <= 0 ? undefined : arguments[0]);
        return axis;
      };
      axis.tickSizeOuter = function () {
        if (!arguments.length) {
          return tickSizeOuter;
        }
        tickSizeOuter = Number(arguments.length <= 0 ? undefined : arguments[0]);
        return axis;
      };
      axis.tickPadding = function () {
        if (!arguments.length) {
          return tickPadding;
        }
        tickPadding = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      axis.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      axis.scale = function () {
        if (!arguments.length) {
          return scale;
        }
        scale = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      axis.ticks = function () {
        for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }
        tickArguments = [].concat(args);
        return axis;
      };
      axis.tickArguments = function () {
        if (!arguments.length) {
          return tickArguments !== null ? tickArguments.slice() : null;
        }
        tickArguments = (arguments.length <= 0 ? undefined : arguments[0]) == null ? [] : _toConsumableArray(arguments.length <= 0 ? undefined : arguments[0]);
        return axis;
      };
      axis.tickValues = function () {
        if (!arguments.length) {
          return tickValues !== null ? tickValues.slice() : null;
        }
        tickValues = (arguments.length <= 0 ? undefined : arguments[0]) == null ? [] : _toConsumableArray(arguments.length <= 0 ? undefined : arguments[0]);
        return axis;
      };
      axis.orient = function () {
        return orient;
      };
      return axis;
    };

    var axis = function axis(orient, scale) {
      var tickCenterLabel = false;
      var labelOffset = function labelOffset(tick, index, ticksArray) {
        var x = 0;
        var y = base.tickSizeInner() + base.tickPadding();
        var hidden = false;
        if (tickCenterLabel) {
          var thisPosition = scale(tick);
          var nextPosition = index < ticksArray.length - 1 ? scale(ticksArray[index + 1]) : scale.range()[1];
          x = (nextPosition - thisPosition) / 2;
          y = base.tickPadding();
          hidden = index === ticksArray.length - 1 && thisPosition === nextPosition;
        }
        return {
          offset: [x, y],
          hidden: hidden
        };
      };
      var base = axisBase(orient, scale, {
        labelOffset: labelOffset
      });
      var axis = function axis(selection) {
        return base(selection);
      };
      axis.tickCenterLabel = function () {
        if (!arguments.length) {
          return tickCenterLabel;
        }
        tickCenterLabel = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      rebindAll(axis, base);
      return axis;
    };
    var axisTop = function axisTop(scale) {
      return axis('top', scale);
    };
    var axisBottom = function axisBottom(scale) {
      return axis('bottom', scale);
    };
    var axisLeft = function axisLeft(scale) {
      return axis('left', scale);
    };
    var axisRight = function axisRight(scale) {
      return axis('right', scale);
    };

    var axisOrdinal = function axisOrdinal(orient, scale) {
      var tickOffset = null;
      var step = function step(tick, index, ticksArray) {
        if (scale.step) {
          // Use the scale step size
          return scale.step();
        }
        var thisPosition = scale(tick);
        if (index < ticksArray.length - 1) {
          // Distance between ticks
          return scale(ticksArray[index + 1]) / thisPosition;
        } else {
          // 2* distance to end
          return (scale.range()[1] - thisPosition) * 2;
        }
      };
      var tickPath = function tickPath(tick, index, ticksArray) {
        var x = 0;
        if (tickOffset) {
          x = tickOffset(tick, index);
        } else {
          x = step(tick, index, ticksArray) / 2;
        }
        return {
          path: [[x, 0], [x, base.tickSizeInner()]],
          hidden: index === ticksArray.length - 1
        };
      };
      var labelOffset = function labelOffset() {
        // Don't include the tickSizeInner in the label positioning
        return {
          offset: [0, base.tickPadding()]
        };
      };
      var base = axisBase(orient, scale, {
        labelOffset: labelOffset,
        tickPath: tickPath
      });
      var axis = function axis(selection) {
        base(selection);
      };
      axis.tickOffset = function () {
        if (!arguments.length) {
          return tickOffset;
        }
        tickOffset = arguments.length <= 0 ? undefined : arguments[0];
        return axis;
      };
      rebindAll(axis, base);
      return axis;
    };
    var axisOrdinalTop = function axisOrdinalTop(scale) {
      return axisOrdinal('top', scale);
    };
    var axisOrdinalBottom = function axisOrdinalBottom(scale) {
      return axisOrdinal('bottom', scale);
    };
    var axisOrdinalLeft = function axisOrdinalLeft(scale) {
      return axisOrdinal('left', scale);
    };
    var axisOrdinalRight = function axisOrdinalRight(scale) {
      return axisOrdinal('right', scale);
    };

    var measureLabels = (function (axis) {
      var measure = function measure(selection) {
        var ticks = ticksArrayForAxis(axis);
        var tickFormatter = tickFormatterForAxis(axis);
        var labels = ticks.map(tickFormatter);
        var tester = selection.append('text');
        var boundingBoxes = labels.map(function (l) {
          return tester.text(l).node().getBBox();
        });
        var maxHeight = Math.max.apply(Math, _toConsumableArray(boundingBoxes.map(function (b) {
          return b.height;
        })));
        var maxWidth = Math.max.apply(Math, _toConsumableArray(boundingBoxes.map(function (b) {
          return b.width;
        })));
        tester.remove();
        return {
          maxHeight: maxHeight,
          maxWidth: maxWidth,
          labelCount: labels.length
        };
      };
      return measure;
    });

    var axisLabelRotate = (function (adaptee) {
      var labelRotate = 'auto';
      var decorate = function decorate() {};
      var isVertical = function isVertical() {
        return adaptee.orient() === 'left' || adaptee.orient() === 'right';
      };
      var sign = function sign() {
        return adaptee.orient() === 'top' || adaptee.orient() === 'left' ? -1 : 1;
      };
      var labelAnchor = function labelAnchor() {
        switch (adaptee.orient()) {
          case 'top':
          case 'right':
            return 'start';
          default:
            return 'end';
        }
      };
      var calculateRotation = function calculateRotation(s) {
        var _measureLabels = measureLabels(adaptee)(s),
          maxHeight = _measureLabels.maxHeight,
          maxWidth = _measureLabels.maxWidth,
          labelCount = _measureLabels.labelCount;
        var measuredSize = labelCount * maxWidth;

        // The more the overlap, the more we rotate
        var rotate;
        if (labelRotate === 'auto') {
          var range = adaptee.scale().range()[1];
          rotate = range < measuredSize ? 90 * Math.min(1, (measuredSize / range - 0.8) / 2) : 0;
        } else {
          rotate = labelRotate;
        }
        return {
          rotate: isVertical() ? Math.floor(sign() * (90 - rotate)) : Math.floor(-rotate),
          maxHeight: maxHeight,
          maxWidth: maxWidth,
          anchor: rotate ? labelAnchor() : 'middle'
        };
      };
      var decorateRotation = function decorateRotation(sel) {
        var _calculateRotation = calculateRotation(sel),
          rotate = _calculateRotation.rotate,
          maxHeight = _calculateRotation.maxHeight,
          anchor = _calculateRotation.anchor;
        var text = sel.select('text');
        var existingTransform = text.attr('transform');
        var offset = sign() * Math.floor(maxHeight / 2);
        var offsetTransform = isVertical() ? "translate(".concat(offset, ", 0)") : "translate(0, ".concat(offset, ")");
        text.style('text-anchor', anchor).attr('transform', "".concat(existingTransform, " ").concat(offsetTransform, " rotate(").concat(rotate, " 0 0)"));
      };
      var axisLabelRotate = function axisLabelRotate(arg) {
        adaptee(arg);
      };
      adaptee.decorate(function (s) {
        decorateRotation(s);
        decorate(s);
      });
      axisLabelRotate.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return axisLabelRotate;
      };
      axisLabelRotate.labelRotate = function () {
        if (!arguments.length) {
          return labelRotate;
        }
        labelRotate = arguments.length <= 0 ? undefined : arguments[0];
        return axisLabelRotate;
      };
      rebindAll(axisLabelRotate, adaptee, exclude('decorate'));
      return axisLabelRotate;
    });

    var axisLabelOffset = (function (adaptee) {
      var labelOffsetDepth = 'auto';
      var decorate = function decorate() {};
      var isVertical = function isVertical() {
        return adaptee.orient() === 'left' || adaptee.orient() === 'right';
      };
      var sign = function sign() {
        return adaptee.orient() === 'top' || adaptee.orient() === 'left' ? -1 : 1;
      };
      var decorateOffset = function decorateOffset(sel) {
        var _measureLabels = measureLabels(adaptee)(sel),
          maxHeight = _measureLabels.maxHeight,
          maxWidth = _measureLabels.maxWidth,
          labelCount = _measureLabels.labelCount;
        var range = adaptee.scale().range()[1];
        var offsetLevels = labelOffsetDepth === 'auto' ? Math.floor((isVertical() ? maxHeight : maxWidth) * labelCount / range) + 1 : labelOffsetDepth;
        var text = sel.select('text');
        var existingTransform = text.attr('transform');
        var transform = function transform(i) {
          return isVertical() ? "translate(".concat(i % offsetLevels * maxWidth * sign(), ", 0)") : "translate(0, ".concat(i % offsetLevels * maxHeight * sign(), ")");
        };
        text.attr('transform', function (_, i) {
          return "".concat(existingTransform, " ").concat(transform(i));
        });
      };
      var axisLabelOffset = function axisLabelOffset(arg) {
        return adaptee(arg);
      };
      adaptee.decorate(function (s) {
        decorateOffset(s);
        decorate(s);
      });
      axisLabelOffset.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return axisLabelOffset;
      };
      axisLabelOffset.labelOffsetDepth = function () {
        if (!arguments.length) {
          return labelOffsetDepth;
        }
        labelOffsetDepth = arguments.length <= 0 ? undefined : arguments[0];
        return axisLabelOffset;
      };
      rebindAll(axisLabelOffset, adaptee, exclude('decorate'));
      return axisLabelOffset;
    });

    var key = '__d3fc-elements__';
    var get = function get(element) {
      return element[key] || {};
    };
    var set = function set(element, data) {
      return void (element[key] = data);
    };
    var clear = function clear(element) {
      return delete element[key];
    };

    var find = function find(element) {
      return element.tagName === 'D3FC-GROUP' ? [element].concat(_toConsumableArray(element.querySelectorAll('d3fc-canvas, d3fc-group, d3fc-svg'))) : [element];
    };
    var measure = function measure(element) {
      var _data$get = get(element),
        previousWidth = _data$get.width,
        previousHeight = _data$get.height;
      var pixelRatio = element.useDevicePixelRatio && window.devicePixelRatio != null ? window.devicePixelRatio : 1;
      var width = element.clientWidth * pixelRatio;
      var height = element.clientHeight * pixelRatio;
      var resized = width !== previousWidth || height !== previousHeight;
      var child = element.children[0];
      set(element, {
        pixelRatio: pixelRatio,
        width: width,
        height: height,
        resized: resized,
        child: child
      });
    };
    if (typeof CustomEvent !== 'function') {
      throw new Error('d3fc-element depends on CustomEvent. Make sure that you load a polyfill in older browsers. See README.');
    }
    var resize = function resize(element) {
      var detail = get(element);
      var event = new CustomEvent('measure', {
        detail: detail
      });
      element.dispatchEvent(event);
    };
    var draw = function draw(element) {
      var detail = get(element);
      var event = new CustomEvent('draw', {
        detail: detail
      });
      element.dispatchEvent(event);
    };
    var redraw = (function (elements) {
      var allElements = elements.map(find).reduce(function (a, b) {
        return a.concat(b);
      });
      allElements.forEach(measure);
      allElements.forEach(resize);
      allElements.forEach(draw);
    });

    var getQueue = function getQueue(element) {
      return get(element.ownerDocument).queue || [];
    };
    var setQueue = function setQueue(element, queue) {
      var _data$get = get(element.ownerDocument),
        requestId = _data$get.requestId;
      if (requestId == null) {
        requestId = requestAnimationFrame(function () {
          // This seems like a weak way of retrieving the queue
          // but I can't see an edge case at the minute...
          var queue = getQueue(element);
          redraw(queue);
          clearQueue(element);
        });
      }
      set(element.ownerDocument, {
        queue: queue,
        requestId: requestId
      });
    };
    var clearQueue = function clearQueue(element) {
      return clear(element.ownerDocument);
    };
    var isDescendentOf = function isDescendentOf(element, ancestor) {
      var node = element;
      do {
        if (node.parentNode === ancestor) {
          return true;
        }
        // eslint-disable-next-line no-cond-assign
      } while (node = node.parentNode);
      return false;
    };
    var _requestRedraw = (function (element) {
      var queue = getQueue(element);
      var queueContainsElement = queue.indexOf(element) > -1;
      if (queueContainsElement) {
        return;
      }
      var queueContainsAncestor = queue.some(function (queuedElement) {
        return isDescendentOf(element, queuedElement);
      });
      if (queueContainsAncestor) {
        return;
      }
      var queueExcludingDescendents = queue.filter(function (queuedElement) {
        return !isDescendentOf(queuedElement, element);
      });
      queueExcludingDescendents.push(element);
      setQueue(element, queueExcludingDescendents);
    });

    if (typeof HTMLElement !== 'function') {
      throw new Error('d3fc-element depends on Custom Elements (v1). Make sure that you load a polyfill in older browsers. See README.');
    }
    var addMeasureListener = function addMeasureListener(element) {
      if (element.__measureListener__ != null) {
        return;
      }
      element.__measureListener__ = function (event) {
        return element.setMeasurements(event.detail);
      };
      element.addEventListener('measure', element.__measureListener__);
    };
    var removeMeasureListener = function removeMeasureListener(element) {
      if (element.__measureListener__ == null) {
        return;
      }
      element.removeEventListener('measure', element.__measureListener__);
      element.__measureListener__ = null;
    };
    var element = (function (createNode, applyMeasurements) {
      return /*#__PURE__*/function (_HTMLElement) {
        _inherits(_class, _HTMLElement);
        var _super = _createSuper(_class);
        function _class() {
          _classCallCheck(this, _class);
          return _super.apply(this, arguments);
        }
        _createClass(_class, [{
          key: "attributeChangedCallback",
          value: function attributeChangedCallback(name) {
            switch (name) {
              case 'use-device-pixel-ratio':
                this.requestRedraw();
                break;
            }
          }
        }, {
          key: "connectedCallback",
          value: function connectedCallback() {
            if (this.childNodes.length === 0) {
              this.appendChild(createNode());
            }
            addMeasureListener(this);
          }
        }, {
          key: "disconnectedCallback",
          value: function disconnectedCallback() {
            removeMeasureListener(this);
          }
        }, {
          key: "setMeasurements",
          value: function setMeasurements(_ref) {
            var width = _ref.width,
              height = _ref.height;
            var _this$childNodes = _toArray(this.childNodes),
              node = _this$childNodes[0],
              other = _this$childNodes.slice(1);
            if (other.length > 0) {
              throw new Error('A d3fc-svg/canvas element must only contain a single svg/canvas element.');
            }
            applyMeasurements(this, node, {
              width: width,
              height: height
            });
          }
        }, {
          key: "useDevicePixelRatio",
          get: function get() {
            return this.hasAttribute('use-device-pixel-ratio') && this.getAttribute('use-device-pixel-ratio') !== 'false';
          },
          set: function set(useDevicePixelRatio) {
            if (useDevicePixelRatio && !this.useDevicePixelRatio) {
              this.setAttribute('use-device-pixel-ratio', '');
            } else if (!useDevicePixelRatio && this.useDevicePixelRatio) {
              this.removeAttribute('use-device-pixel-ratio');
            }
            this.requestRedraw();
          }
        }, {
          key: "requestRedraw",
          value: function requestRedraw() {
            _requestRedraw(this);
          }
        }], [{
          key: "observedAttributes",
          get: function get() {
            return ['use-device-pixel-ratio'];
          }
        }]);
        return _class;
      }( /*#__PURE__*/_wrapNativeSuper(HTMLElement));
    });

    var _default$1 = /*#__PURE__*/function (_element) {
      _inherits(_default, _element);
      var _super = _createSuper(_default);
      function _default() {
        _classCallCheck(this, _default);
        return _super.apply(this, arguments);
      }
      _createClass(_default, [{
        key: "setWebglViewport",
        get: function get() {
          return this.hasAttribute('set-webgl-viewport') && this.getAttribute('set-webgl-viewport') !== 'false';
        },
        set: function set(setWebglViewport) {
          if (setWebglViewport && !this.setWebglViewport) {
            this.setAttribute('set-webgl-viewport', '');
          } else if (!setWebglViewport && this.setWebglViewport) {
            this.removeAttribute('set-webgl-viewport');
          }
          this.requestRedraw();
        }
      }]);
      return _default;
    }(element(function () {
      return document.createElement('canvas');
    }, function (element, node, _ref) {
      var width = _ref.width,
        height = _ref.height;
      node.setAttribute('width', width);
      node.setAttribute('height', height);
      if (element.setWebglViewport) {
        var context = node.getContext('webgl');
        context.viewport(0, 0, width, height);
      }
    }));

    var updateAutoResize = function updateAutoResize(element) {
      if (element.autoResize) {
        addAutoResizeListener(element);
      } else {
        removeAutoResizeListener(element);
      }
    };
    var addAutoResizeListener = function addAutoResizeListener(element) {
      if (element.__autoResizeListener__ != null) {
        return;
      }
      element.__autoResizeListener__ = function () {
        return _requestRedraw(element);
      };
      addEventListener('resize', element.__autoResizeListener__);
    };
    var removeAutoResizeListener = function removeAutoResizeListener(element) {
      if (element.__autoResizeListener__ == null) {
        return;
      }
      removeEventListener('resize', element.__autoResizeListener__);
      element.__autoResizeListener__ = null;
    };
    var _default = /*#__PURE__*/function (_HTMLElement) {
      _inherits(_default, _HTMLElement);
      var _super = _createSuper(_default);
      function _default() {
        _classCallCheck(this, _default);
        return _super.apply(this, arguments);
      }
      _createClass(_default, [{
        key: "connectedCallback",
        value: function connectedCallback() {
          updateAutoResize(this);
        }
      }, {
        key: "disconnectedCallback",
        value: function disconnectedCallback() {
          removeAutoResizeListener(this);
        }
      }, {
        key: "requestRedraw",
        value: function requestRedraw() {
          _requestRedraw(this);
        }
      }, {
        key: "autoResize",
        get: function get() {
          return this.hasAttribute('auto-resize') && this.getAttribute('auto-resize') !== 'false';
        },
        set: function set(autoResize) {
          if (autoResize && !this.autoResize) {
            this.setAttribute('auto-resize', '');
          } else if (!autoResize && this.autoResize) {
            this.removeAttribute('auto-resize');
          }
          updateAutoResize(this);
        }
      }, {
        key: "attributeChangedCallback",
        value: function attributeChangedCallback(name) {
          switch (name) {
            case 'auto-resize':
              updateAutoResize(this);
              break;
          }
        }
      }], [{
        key: "observedAttributes",
        get: function get() {
          return ['auto-resize'];
        }
      }]);
      return _default;
    }( /*#__PURE__*/_wrapNativeSuper(HTMLElement));

    var Svg = element(function () {
      return document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    }, function (element, node, _ref) {
      var width = _ref.width,
        height = _ref.height;
      node.setAttribute('viewBox', "0 0 ".concat(width, " ").concat(height));
    });

    // Adapted from https://github.com/substack/insert-css
    var css$1 = "d3fc-canvas,d3fc-svg{position:relative;display:block}d3fc-canvas>canvas,d3fc-svg>svg{position:absolute;height:100%;width:100%}d3fc-svg>svg{overflow:visible}";
    var styleElement$1 = document.createElement('style');
    styleElement$1.setAttribute('type', 'text/css');
    document.querySelector('head').appendChild(styleElement$1);
    if (styleElement$1.styleSheet) {
      styleElement$1.styleSheet.cssText += css$1;
    } else {
      styleElement$1.textContent += css$1;
    }

    if ((typeof customElements === "undefined" ? "undefined" : _typeof(customElements)) !== 'object' || typeof customElements.define !== 'function') {
      throw new Error('d3fc-element depends on Custom Elements (v1). Make sure that you load a polyfill in older browsers. See README.');
    }
    var alreadyRegistered = [];
    var registerElement = function registerElement(name, element) {
      if (customElements.get(name)) {
        alreadyRegistered.push(name);
      } else {
        customElements.define(name, element);
      }
    };
    registerElement('d3fc-canvas', _default$1);
    registerElement('d3fc-group', _default);
    registerElement('d3fc-svg', Svg);
    if (alreadyRegistered.length > 0) {
      console.warn("The d3fc components \"".concat(alreadyRegistered.join(', '), "\" is/are already registered on window. Be aware that this can create compatibility issues if different versions are used."));
    }

    var pointer = (function () {
      var pointEvent = d3Dispatch.dispatch('point');
      function mousemove(event) {
        var point = d3Selection.pointer(event);
        pointEvent.call('point', this, [{
          x: point[0],
          y: point[1]
        }]);
      }
      function mouseleave() {
        void pointEvent.call('point', this, []);
      }
      var instance = function instance(selection) {
        selection.on('mouseenter.pointer', mousemove).on('mousemove.pointer', mousemove).on('mouseleave.pointer', mouseleave);
      };
      rebind(instance, pointEvent, 'on');
      return instance;
    });

    var group = (function () {
      var key = '';
      var orient = 'vertical';
      // D3 CSV returns all values as strings, this converts them to numbers
      // by default.
      var value = function value(row, column) {
        return Number(row[column]);
      };
      var verticalgroup = function verticalgroup(data) {
        return Object.keys(data[0]).filter(function (k) {
          return k !== key;
        }).map(function (k) {
          var values = data.filter(function (row) {
            return row[k];
          }).map(function (row) {
            var cell = [row[key], value(row, k)];
            cell.data = row;
            return cell;
          });
          values.key = k;
          return values;
        });
      };
      var horizontalgroup = function horizontalgroup(data) {
        return data.map(function (row) {
          var values = Object.keys(row).filter(function (d) {
            return d !== key;
          }).map(function (k) {
            var cell = [k, value(row, k)];
            cell.data = row;
            return cell;
          });
          values.key = row[key];
          return values;
        });
      };
      var group = function group(data) {
        return orient === 'vertical' ? verticalgroup(data) : horizontalgroup(data);
      };
      group.key = function () {
        if (!arguments.length) {
          return key;
        }
        key = arguments.length <= 0 ? undefined : arguments[0];
        return group;
      };
      group.value = function () {
        if (!arguments.length) {
          return value;
        }
        value = arguments.length <= 0 ? undefined : arguments[0];
        return group;
      };
      group.orient = function () {
        if (!arguments.length) {
          return orient;
        }
        orient = arguments.length <= 0 ? undefined : arguments[0];
        return group;
      };
      return group;
    });

    var store = (function () {
      var data = {};
      var store = function store(target) {
        for (var _i = 0, _Object$keys = Object.keys(data); _i < _Object$keys.length; _i++) {
          var key = _Object$keys[_i];
          target[key].apply(null, data[key]);
        }
        return target;
      };
      for (var _len = arguments.length, names = new Array(_len), _key = 0; _key < _len; _key++) {
        names[_key] = arguments[_key];
      }
      var _loop = function _loop() {
        var name = _names[_i2];
        store[name] = function () {
          for (var _len2 = arguments.length, args = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
            args[_key2] = arguments[_key2];
          }
          if (!args.length) {
            return data[name];
          }
          data[name] = args;
          return store;
        };
      };
      for (var _i2 = 0, _names = names; _i2 < _names.length; _i2++) {
        _loop();
      }
      return store;
    });

    // Adapted from https://github.com/substack/insert-css
    var css = "d3fc-group.cartesian-chart{width:100%;height:100%;overflow:hidden;display:grid;display:-ms-grid;grid-template-columns:minmax(1em,max-content) auto 1fr auto minmax(1em,max-content);-ms-grid-columns:minmax(1em,max-content) auto 1fr auto minmax(1em,max-content);grid-template-rows:minmax(1em,max-content) auto 1fr auto minmax(1em,max-content);-ms-grid-rows:minmax(1em,max-content) auto 1fr auto minmax(1em,max-content);}\nd3fc-group.cartesian-chart>.top-label{align-self:center;-ms-grid-column-align:center;justify-self:center;-ms-grid-row-align:center;grid-column:3;-ms-grid-column:3;grid-row:1;-ms-grid-row:1;}\nd3fc-group.cartesian-chart>.top-axis{height:2em;grid-column:3;-ms-grid-column:3;grid-row:2;-ms-grid-row:2;}\nd3fc-group.cartesian-chart>.left-label{align-self:center;-ms-grid-column-align:center;justify-self:center;-ms-grid-row-align:center;grid-column:1;-ms-grid-column:1;grid-row:3;-ms-grid-row:3;}\nd3fc-group.cartesian-chart>.left-axis{width:3em;grid-column:2;-ms-grid-column:2;grid-row:3;-ms-grid-row:3;}\nd3fc-group.cartesian-chart>.plot-area{overflow:hidden;grid-column:3;-ms-grid-column:3;grid-row:3;-ms-grid-row:3;}\nd3fc-group.cartesian-chart>.right-axis{width:3em;grid-column:4;-ms-grid-column:4;grid-row:3;-ms-grid-row:3;}\nd3fc-group.cartesian-chart>.right-label{align-self:center;-ms-grid-column-align:center;justify-self:center;-ms-grid-row-align:center;grid-column:5;-ms-grid-column:5;grid-row:3;-ms-grid-row:3;}\nd3fc-group.cartesian-chart>.bottom-axis{height:2em;grid-column:3;-ms-grid-column:3;grid-row:4;-ms-grid-row:4;}\nd3fc-group.cartesian-chart>.bottom-label{align-self:center;-ms-grid-column-align:center;justify-self:center;-ms-grid-row-align:center;grid-column:3;-ms-grid-column:3;grid-row:5;-ms-grid-row:5;}\nd3fc-group.cartesian-chart>.y-label{display:flex;transform:rotate(-90deg);width:1em;white-space:nowrap;justify-content:center;}";
    var styleElement = document.createElement('style');
    styleElement.setAttribute('type', 'text/css');
    document.querySelector('head').appendChild(styleElement);
    if (styleElement.styleSheet) {
      styleElement.styleSheet.cssText += css;
    } else {
      styleElement.textContent += css;
    }

    var functor$1 = function functor(v) {
      return typeof v === 'function' ? v : function () {
        return v;
      };
    };
    var cartesianChart = (function () {
      var _getArguments = getArguments.apply(void 0, arguments),
        xScale = _getArguments.xScale,
        yScale = _getArguments.yScale,
        xAxis = _getArguments.xAxis,
        yAxis = _getArguments.yAxis;
      var chartLabel = functor$1('');
      var xLabel = functor$1('');
      var yLabel = functor$1('');
      var xAxisHeight = functor$1(null);
      var yAxisWidth = functor$1(null);
      var yOrient = functor$1('right');
      var xOrient = functor$1('bottom');
      var webglPlotArea = null;
      var canvasPlotArea = null;
      var svgPlotArea = null;
      var isContextLost = false;
      var useDevicePixelRatio = true;
      var xAxisStore = store('tickFormat', 'ticks', 'tickArguments', 'tickSize', 'tickSizeInner', 'tickSizeOuter', 'tickValues', 'tickPadding', 'tickCenterLabel');
      var xDecorate = function xDecorate() {};
      var yAxisStore = store('tickFormat', 'ticks', 'tickArguments', 'tickSize', 'tickSizeInner', 'tickSizeOuter', 'tickValues', 'tickPadding', 'tickCenterLabel');
      var yDecorate = function yDecorate() {};
      var decorate = function decorate() {};
      var containerDataJoin = dataJoin('d3fc-group', 'cartesian-chart');
      var webglDataJoin = dataJoin('d3fc-canvas', 'webgl-plot-area');
      var canvasDataJoin = dataJoin('d3fc-canvas', 'canvas-plot-area');
      var svgDataJoin = dataJoin('d3fc-svg', 'svg-plot-area');
      var xAxisDataJoin = dataJoin('d3fc-svg', 'x-axis').key(function (d) {
        return d;
      });
      var yAxisDataJoin = dataJoin('d3fc-svg', 'y-axis').key(function (d) {
        return d;
      });
      var chartLabelDataJoin = dataJoin('div', 'chart-label');
      var xLabelDataJoin = dataJoin('div', 'x-label').key(function (d) {
        return d;
      });
      var yLabelDataJoin = dataJoin('div', 'y-label').key(function (d) {
        return d;
      });
      var propagateTransition = function propagateTransition(maybeTransition) {
        return function (selection) {
          return isTransition(maybeTransition) ? selection.transition(maybeTransition) : selection;
        };
      };
      var cartesian = function cartesian(selection) {
        var transitionPropagator = propagateTransition(selection);
        selection.each(function (data, index, group) {
          var container = containerDataJoin(d3Selection.select(group[index]), [data]);
          container.enter().attr('auto-resize', '');
          chartLabelDataJoin(container, [xOrient(data)]).attr('class', function (d) {
            return d === 'top' ? 'chart-label bottom-label' : 'chart-label top-label';
          }).style('margin-bottom', function (d) {
            return d === 'top' ? 0 : '1em';
          }).style('margin-top', function (d) {
            return d === 'top' ? '1em' : 0;
          }).text(chartLabel(data));
          xLabelDataJoin(container, [xOrient(data)]).attr('class', function (d) {
            return "x-label ".concat(d, "-label");
          }).text(xLabel(data));
          yLabelDataJoin(container, [yOrient(data)]).attr('class', function (d) {
            return "y-label ".concat(d, "-label");
          }).text(yLabel(data));
          webglDataJoin(container, webglPlotArea ? [data] : []).attr('set-webgl-viewport', '').classed('plot-area', true).attr('use-device-pixel-ratio', useDevicePixelRatio).on('draw', function (event, d) {
            var _event$detail = event.detail,
              child = _event$detail.child,
              pixelRatio = _event$detail.pixelRatio;
            webglPlotArea.context(isContextLost ? null : child.getContext('webgl')).pixelRatio(pixelRatio).xScale(xScale).yScale(yScale);
            webglPlotArea(d);
          });
          container.select('.webgl-plot-area>canvas').on('webglcontextlost', function (event) {
            console.warn('WebGLRenderingContext lost');
            event.preventDefault();
            isContextLost = true;
            container.node().requestRedraw();
          }).on('webglcontextrestored', function () {
            console.info('WebGLRenderingContext restored');
            isContextLost = false;
            container.node().requestRedraw();
          });
          canvasDataJoin(container, canvasPlotArea ? [data] : []).classed('plot-area', true).attr('use-device-pixel-ratio', useDevicePixelRatio).on('draw', function (event, d) {
            var _event$detail2 = event.detail,
              child = _event$detail2.child,
              pixelRatio = _event$detail2.pixelRatio;
            var context = child.getContext('2d');
            context.save();
            if (useDevicePixelRatio) {
              context.scale(pixelRatio, pixelRatio);
            }
            canvasPlotArea.context(context).xScale(xScale).yScale(yScale);
            canvasPlotArea(d);
            context.restore();
          });
          svgDataJoin(container, svgPlotArea ? [data] : []).classed('plot-area', true).on('draw', function (event, d) {
            var child = event.detail.child;
            svgPlotArea.xScale(xScale).yScale(yScale);
            transitionPropagator(d3Selection.select(child).datum(d)).call(svgPlotArea);
          });
          xAxisDataJoin(container, [xOrient(data)]).attr('class', function (d) {
            return "x-axis ".concat(d, "-axis");
          }).style('height', xAxisHeight(data)).on('measure', function (event, d) {
            var _event$detail3 = event.detail,
              width = _event$detail3.width,
              height = _event$detail3.height,
              child = _event$detail3.child;
            if (d === 'top') {
              d3Selection.select(child).attr('viewBox', "0 ".concat(-height, " ").concat(width, " ").concat(height));
            }
            xScale.range([0, width]);
          }).on('draw', function (event, d) {
            var child = event.detail.child;
            var xAxisComponent = d === 'top' ? xAxis.top(xScale) : xAxis.bottom(xScale);
            xAxisComponent.decorate(xDecorate);
            transitionPropagator(d3Selection.select(child).datum(d)).call(xAxisStore(xAxisComponent));
          });
          yAxisDataJoin(container, [yOrient(data)]).attr('class', function (d) {
            return "y-axis ".concat(d, "-axis");
          }).style('width', yAxisWidth(data)).on('measure', function (event, d) {
            var _event$detail4 = event.detail,
              width = _event$detail4.width,
              height = _event$detail4.height,
              child = _event$detail4.child;
            if (d === 'left') {
              d3Selection.select(child).attr('viewBox', "".concat(-width, " 0 ").concat(width, " ").concat(height));
            }
            yScale.range([height, 0]);
          }).on('draw', function (event, d) {
            var child = event.detail.child;
            var yAxisComponent = d === 'left' ? yAxis.left(yScale) : yAxis.right(yScale);
            yAxisComponent.decorate(yDecorate);
            transitionPropagator(d3Selection.select(child).datum(d)).call(yAxisStore(yAxisComponent));
          });
          container.each(function (d, i, nodes) {
            return nodes[i].requestRedraw();
          });
          decorate(container, data, index);
        });
      };
      var scaleExclusions = exclude(/range\w*/,
      // the scale range is set via the component layout
      /tickFormat/ // use axis.tickFormat instead (only present on linear scales)
      );
      rebindAll(cartesian, xScale, scaleExclusions, prefix('x'));
      rebindAll(cartesian, yScale, scaleExclusions, prefix('y'));
      rebindAll(cartesian, xAxisStore, prefix('x'));
      rebindAll(cartesian, yAxisStore, prefix('y'));
      cartesian.xOrient = function () {
        if (!arguments.length) {
          return xOrient;
        }
        xOrient = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.yOrient = function () {
        if (!arguments.length) {
          return yOrient;
        }
        yOrient = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.xDecorate = function () {
        if (!arguments.length) {
          return xDecorate;
        }
        xDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.yDecorate = function () {
        if (!arguments.length) {
          return yDecorate;
        }
        yDecorate = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.chartLabel = function () {
        if (!arguments.length) {
          return chartLabel;
        }
        chartLabel = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.xLabel = function () {
        if (!arguments.length) {
          return xLabel;
        }
        xLabel = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.yLabel = function () {
        if (!arguments.length) {
          return yLabel;
        }
        yLabel = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.xAxisHeight = function () {
        if (!arguments.length) {
          return xAxisHeight;
        }
        xAxisHeight = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.yAxisWidth = function () {
        if (!arguments.length) {
          return yAxisWidth;
        }
        yAxisWidth = functor$1(arguments.length <= 0 ? undefined : arguments[0]);
        return cartesian;
      };
      cartesian.webglPlotArea = function () {
        if (!arguments.length) {
          return webglPlotArea;
        }
        webglPlotArea = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.canvasPlotArea = function () {
        if (!arguments.length) {
          return canvasPlotArea;
        }
        canvasPlotArea = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.svgPlotArea = function () {
        if (!arguments.length) {
          return svgPlotArea;
        }
        svgPlotArea = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.decorate = function () {
        if (!arguments.length) {
          return decorate;
        }
        decorate = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      cartesian.useDevicePixelRatio = function () {
        if (!arguments.length) {
          return useDevicePixelRatio;
        }
        useDevicePixelRatio = arguments.length <= 0 ? undefined : arguments[0];
        return cartesian;
      };
      return cartesian;
    });
    var getArguments = function getArguments() {
      var defaultSettings = {
        xScale: d3Scale.scaleIdentity(),
        yScale: d3Scale.scaleIdentity(),
        xAxis: {
          bottom: axisBottom,
          top: axisTop
        },
        yAxis: {
          right: axisRight,
          left: axisLeft
        }
      };
      for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }
      if (args.length === 1 && !args[0].domain && !args[0].range) {
        // Settings object
        return Object.assign(defaultSettings, args[0]);
      }

      // xScale/yScale parameters
      return Object.assign(defaultSettings, {
        xScale: args[0] || defaultSettings.xScale,
        yScale: args[1] || defaultSettings.yScale
      });
    };

    var functor = function functor(v) {
      return typeof v === 'function' ? v : function () {
        return v;
      };
    };
    var cartesianBase = (function (setPlotArea, defaultPlotArea) {
      return function () {
        var yLabel = functor('');
        var plotArea = defaultPlotArea;
        var decorate = function decorate() {};
        var cartesian = cartesianChart.apply(void 0, arguments);
        var cartesianBase = function cartesianBase(selection) {
          setPlotArea(cartesian, plotArea);
          cartesian.decorate(function (container, data, index) {
            container.enter().select('.x-label').style('height', '1em').style('line-height', '1em');
            var yOrientValue = cartesian.yOrient()(data);
            container.enter().append('div').attr('class', 'y-label-container').style('grid-column', yOrientValue === 'left' ? 1 : 5).style('-ms-grid-column', yOrientValue === 'left' ? 1 : 5).style('grid-row', 3).style('-ms-grid-row', 3).style('width', '1em').style('display', 'flex').style('align-items', 'center').style('justify-content', 'center').style('white-space', 'nowrap').append('div').attr('class', 'y-label').style('transform', 'rotate(-90deg)');
            container.select('.y-label-container>.y-label').text(yLabel);
            decorate(container, data, index);
          });
          selection.call(cartesian);
        };
        rebindAll(cartesianBase, cartesian, include(/^x/, /^y/, 'chartLabel'));
        cartesianBase.yLabel = function () {
          if (!arguments.length) {
            return yLabel;
          }
          yLabel = functor(arguments.length <= 0 ? undefined : arguments[0]);
          return cartesianBase;
        };
        cartesianBase.plotArea = function () {
          if (!arguments.length) {
            return plotArea;
          }
          plotArea = arguments.length <= 0 ? undefined : arguments[0];
          return cartesianBase;
        };
        cartesianBase.decorate = function () {
          if (!arguments.length) {
            return decorate;
          }
          decorate = arguments.length <= 0 ? undefined : arguments[0];
          return cartesianBase;
        };
        return cartesianBase;
      };
    });

    var cartesian$1 = cartesianBase(function (cartesian, plotArea) {
      return cartesian.svgPlotArea(plotArea);
    }, seriesSvgLine);

    var cartesian = cartesianBase(function (cartesian, plotArea) {
      return cartesian.canvasPlotArea(plotArea);
    }, seriesCanvasLine);

    var brushForOrient = function brushForOrient(orient) {
      switch (orient) {
        case 'x':
          return d3Brush.brushX();
        case 'y':
          return d3Brush.brushY();
        case 'xy':
          return d3Brush.brush();
      }
    };
    var invertRange = function invertRange(range) {
      return [range[1], range[0]];
    };
    var brushBase = function brushBase(orient) {
      var brush = brushForOrient(orient);
      var eventDispatch = d3Dispatch.dispatch('brush', 'start', 'end');
      var xScale = d3Scale.scaleIdentity();
      var yScale = d3Scale.scaleIdentity();
      var innerJoin = dataJoin('g', 'brush');
      var mapSelection = function mapSelection(selection, xMapping, yMapping) {
        switch (orient) {
          case 'x':
            return selection.map(xMapping);
          case 'y':
            return selection.map(yMapping);
          case 'xy':
            return [[xMapping(selection[0][0]), yMapping(selection[0][1])], [xMapping(selection[1][0]), yMapping(selection[1][1])]];
        }
      };
      var percentToSelection = function percentToSelection(percent) {
        return mapSelection(percent, d3Scale.scaleLinear().domain(xScale.range()).invert, d3Scale.scaleLinear().domain(invertRange(yScale.range())).invert);
      };
      var selectionToPercent = function selectionToPercent(selection) {
        return mapSelection(selection, d3Scale.scaleLinear().domain(xScale.range()), d3Scale.scaleLinear().domain(invertRange(yScale.range())));
      };
      var updateXDomain = function updateXDomain(selection) {
        var f = d3Scale.scaleLinear().domain(xScale.domain());
        if (orient === 'x') {
          return selection.map(f.invert);
        } else if (orient === 'xy') {
          return [f.invert(selection[0][0]), f.invert(selection[1][0])];
        }
      };
      var updateYDomain = function updateYDomain(selection) {
        var g = d3Scale.scaleLinear().domain(invertRange(yScale.domain()));
        if (orient === 'y') {
          return [selection[1], selection[0]].map(g.invert);
        } else if (orient === 'xy') {
          return [g.invert(selection[1][1]), g.invert(selection[0][1])];
        }
      };
      var transformEvent = function transformEvent(event) {
        // The render function calls brush.move, which triggers, start, brush and end events. We don't
        // really want those events so suppress them.
        if (event.sourceEvent && event.sourceEvent.type === 'draw') return;
        if (event.selection) {
          var mappedSelection = selectionToPercent(event.selection);
          eventDispatch.call(event.type, {}, {
            selection: mappedSelection,
            xDomain: updateXDomain(mappedSelection),
            yDomain: updateYDomain(mappedSelection)
          });
        } else {
          eventDispatch.call(event.type, {}, {});
        }
      };
      var base = function base(selection) {
        selection.each(function (data, index, group) {
          // set the extent
          brush.extent([[xScale.range()[0], yScale.range()[1]], [xScale.range()[1], yScale.range()[0]]]);

          // forwards events
          brush.on('end', function (event) {
            return transformEvent(event);
          }).on('brush', function (event) {
            return transformEvent(event);
          }).on('start', function (event) {
            return transformEvent(event);
          });

          // render
          var container = innerJoin(d3Selection.select(group[index]), [data]);
          container.call(brush).call(brush.move, data ? percentToSelection(data) : null);
        });
      };
      base.xScale = function () {
        if (!arguments.length) {
          return xScale;
        }
        xScale = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      base.yScale = function () {
        if (!arguments.length) {
          return yScale;
        }
        yScale = arguments.length <= 0 ? undefined : arguments[0];
        return base;
      };
      rebind(base, eventDispatch, 'on');
      rebind(base, brush, 'filter', 'handleSize');
      return base;
    };
    var brushX = function brushX() {
      return brushBase('x');
    };
    var brushY = function brushY() {
      return brushBase('y');
    };
    var brush = function brush() {
      return brushBase('xy');
    };

    var domainsEqual = function domainsEqual(a, b) {
      if (a == null && b == null) {
        return true;
      }
      var aDomain = a.domain();
      var bDomain = b.domain();
      return aDomain.length === bDomain.length && aDomain.every(function (d, i) {
        var _bDomain$i;
        return (d === null || d === void 0 ? void 0 : d.valueOf()) === ((_bDomain$i = bDomain[i]) === null || _bDomain$i === void 0 ? void 0 : _bDomain$i.valueOf());
      });
    };
    var subtract = function subtract(a, b) {
      return d3Zoom.zoomIdentity.scale(a.k / b.k).translate(a.x - b.x, a.y - b.y);
    };
    var symbol = Symbol('d3fc-domain-zoom');
    var zoom = (function () {
      var dispatcher = d3Dispatch.dispatch('zoom');
      var zoomer = d3Zoom.zoom().on('zoom', function (e) {
        var transform = e.transform;
        var node = this;
        var updatedTransform = transform;
        var _node$symbol = node[symbol],
          originalXScale = _node$symbol.originalXScale,
          previousXScale = _node$symbol.previousXScale,
          xScale = _node$symbol.xScale,
          originalYScale = _node$symbol.originalYScale,
          previousYScale = _node$symbol.previousYScale,
          yScale = _node$symbol.yScale,
          previousTransform = _node$symbol.previousTransform;
        if (!domainsEqual(previousXScale, xScale) || !domainsEqual(previousYScale, yScale)) {
          originalXScale = xScale === null || xScale === void 0 ? void 0 : xScale.copy();
          originalYScale = yScale === null || yScale === void 0 ? void 0 : yScale.copy();
          updatedTransform = subtract(transform, previousTransform);
        }
        if (xScale != null) {
          previousXScale = updatedTransform.rescaleX(originalXScale.range(xScale.range()));
          xScale.domain(previousXScale.domain());
        }
        if (yScale != null) {
          previousYScale = updatedTransform.rescaleY(originalYScale.range(yScale.range()));
          yScale.domain(previousYScale.domain());
        }
        previousTransform = updatedTransform;
        node[symbol] = {
          originalXScale: originalXScale,
          previousXScale: previousXScale,
          xScale: xScale,
          originalYScale: originalYScale,
          previousYScale: previousYScale,
          yScale: yScale,
          previousTransform: previousTransform
        };
        if (updatedTransform !== transform) {
          zoomer.transform(d3Selection.select(node), updatedTransform);
        }
        dispatcher.call('zoom', this, e);
      });
      var instance = function instance(selection) {
        var xScale = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
        var yScale = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
        if (xScale == null && yScale == null) {
          console.warn("Without an xScale and/or yScale specified, this component won't do anything. Perhaps you forgot to specify them e.g. selection.call(zoom, x, y)?");
        }
        selection.each(function (d, i, nodes) {
          var existingContext = nodes[i][symbol];
          if (existingContext != null && existingContext.xScale === xScale && existingContext.yScale === yScale) {
            console.warn("This component should only be called on a selection once. Perhaps you're missing an .enter()?");
          }
          var xScaleCopy = xScale === null || xScale === void 0 ? void 0 : xScale.copy();
          var yScaleCopy = yScale === null || yScale === void 0 ? void 0 : yScale.copy();
          nodes[i][symbol] = {
            originalXScale: xScaleCopy,
            previousXScale: xScaleCopy,
            xScale: xScale,
            originalYScale: yScaleCopy,
            previousYScale: yScaleCopy,
            yScale: yScale,
            previousTransform: d3Zoom.zoomIdentity
          };
        }).call(zoomer);
      };
      rebind(instance, dispatcher, 'on');
      rebind(instance, zoomer, 'extent', 'filter', 'wheelDelta', 'touchable', 'clickDistance', 'tapDistance', 'duration', 'interpolate', 'scaleExtent', 'translateExtent');
      return instance;
    });

    exports.annotationCanvasBand = band;
    exports.annotationCanvasCrosshair = crosshair;
    exports.annotationCanvasGridline = gridline;
    exports.annotationCanvasLine = annotationLine;
    exports.annotationSvgBand = band$1;
    exports.annotationSvgCrosshair = crosshair$1;
    exports.annotationSvgGridline = gridline$1;
    exports.annotationSvgLine = annotationLine$1;
    exports.autoBandwidth = autoBandwidth;
    exports.axisBottom = axisBottom;
    exports.axisLabelOffset = axisLabelOffset;
    exports.axisLabelRotate = axisLabelRotate;
    exports.axisLeft = axisLeft;
    exports.axisOrdinalBottom = axisOrdinalBottom;
    exports.axisOrdinalLeft = axisOrdinalLeft;
    exports.axisOrdinalRight = axisOrdinalRight;
    exports.axisOrdinalTop = axisOrdinalTop;
    exports.axisRight = axisRight;
    exports.axisTop = axisTop;
    exports.brush = brush;
    exports.brushX = brushX;
    exports.brushY = brushY;
    exports.bucket = bucket;
    exports.chartCanvasCartesian = cartesian;
    exports.chartCartesian = cartesianChart;
    exports.chartSvgCartesian = cartesian$1;
    exports.dataJoin = dataJoin;
    exports.discontinuityIdentity = identity$4;
    exports.discontinuityRange = provider;
    exports.discontinuitySkipUtcWeekends = skipUtcWeekends;
    exports.discontinuitySkipUtcWeeklyPattern = skipUtcWeeklyPattern;
    exports.discontinuitySkipWeekends = skipWeekends$1;
    exports.discontinuitySkipWeeklyPattern = skipWeeklyPattern;
    exports.effectivelyZero = effectivelyZero;
    exports.exclude = exclude;
    exports.extentDate = time;
    exports.extentLinear = linearExtent;
    exports.extentTime = time;
    exports.feedGdax = gdax;
    exports.group = group;
    exports.include = include;
    exports.includeMap = includeMap;
    exports.indicatorBollingerBands = bollingerBands;
    exports.indicatorElderRay = elderRay;
    exports.indicatorEnvelope = envelope;
    exports.indicatorExponentialMovingAverage = exponentialMovingAverage;
    exports.indicatorForceIndex = forceIndex;
    exports.indicatorMacd = macd;
    exports.indicatorMovingAverage = movingAverage;
    exports.indicatorRelativeStrengthIndex = relativeStrengthIndex;
    exports.indicatorStochasticOscillator = stochasticOscillator;
    exports.isTransition = isTransition;
    exports.largestTriangleOneBucket = largestTriangleOneBucket;
    exports.largestTriangleThreeBucket = largestTriangleThreeBucket;
    exports.layoutAnnealing = annealing;
    exports.layoutBoundingBox = boundingBox;
    exports.layoutGreedy = greedy;
    exports.layoutLabel = label;
    exports.layoutRemoveOverlaps = removeOverlaps;
    exports.layoutTextLabel = textLabel;
    exports.modeMedian = modeMedian;
    exports.pointer = pointer;
    exports.prefix = prefix;
    exports.randomFinancial = financial;
    exports.randomGeometricBrownianMotion = geometricBrownianMotion;
    exports.randomSkipWeekends = skipWeekends;
    exports.rebind = rebind;
    exports.rebindAll = rebindAll;
    exports.scaleDiscontinuous = discontinuous;
    exports.seriesCanvasArea = area$1;
    exports.seriesCanvasBar = bar$1;
    exports.seriesCanvasBoxPlot = boxPlot$1;
    exports.seriesCanvasCandlestick = candlestick$1;
    exports.seriesCanvasErrorBar = errorBar$1;
    exports.seriesCanvasGrouped = grouped;
    exports.seriesCanvasHeatmap = heatmap;
    exports.seriesCanvasLine = seriesCanvasLine;
    exports.seriesCanvasMulti = seriesCanvasMulti;
    exports.seriesCanvasOhlc = ohlc$1;
    exports.seriesCanvasPoint = seriesCanvasPoint;
    exports.seriesCanvasRepeat = repeat$1;
    exports.seriesSvgArea = area$2;
    exports.seriesSvgBar = bar$2;
    exports.seriesSvgBoxPlot = boxPlot$2;
    exports.seriesSvgCandlestick = candlestick$2;
    exports.seriesSvgErrorBar = errorBar$2;
    exports.seriesSvgGrouped = grouped$1;
    exports.seriesSvgHeatmap = heatmap$1;
    exports.seriesSvgLine = seriesSvgLine;
    exports.seriesSvgMulti = seriesSvgMulti;
    exports.seriesSvgOhlc = ohlc$2;
    exports.seriesSvgPoint = seriesSvgPoint;
    exports.seriesSvgRepeat = repeat$2;
    exports.seriesWebglArea = area;
    exports.seriesWebglBar = bar;
    exports.seriesWebglBoxPlot = boxPlot;
    exports.seriesWebglCandlestick = candlestick;
    exports.seriesWebglErrorBar = errorBar;
    exports.seriesWebglLine = line;
    exports.seriesWebglMulti = multiSeries;
    exports.seriesWebglOhlc = ohlc;
    exports.seriesWebglPoint = point;
    exports.seriesWebglRepeat = repeat;
    exports.shapeBar = shapeBar;
    exports.shapeBoxPlot = shapeBoxPlot;
    exports.shapeCandlestick = shapeCandlestick;
    exports.shapeErrorBar = shapeErrorBar;
    exports.shapeOhlc = shapeOhlc;
    exports.webglAdjacentAttribute = webglAdjacentAttribute;
    exports.webglAttribute = webglAttribute;
    exports.webglBaseAttribute = baseAttributeBuilder;
    exports.webglBufferBuilder = bufferBuilder;
    exports.webglElementIndices = elementIndices;
    exports.webglFillColor = fillColor;
    exports.webglProgramBuilder = programBuilder;
    exports.webglScaleLinear = linear;
    exports.webglScaleLog = log;
    exports.webglScaleMapper = webglScaleMapper;
    exports.webglScalePow = pow;
    exports.webglSeriesArea = webglSeriesArea;
    exports.webglSeriesBar = webglSeriesBar;
    exports.webglSeriesBoxPlot = webglSeriesBoxPlot;
    exports.webglSeriesCandlestick = webglSeriesCandlestick;
    exports.webglSeriesErrorBar = webglSeriesErrorBar;
    exports.webglSeriesLine = webglSeriesLine;
    exports.webglSeriesOhlc = webglSeriesOhlc;
    exports.webglSeriesPoint = webglSeriesPoint;
    exports.webglShaderBuilder = shaderBuilder;
    exports.webglStrokeColor = strokeColor;
    exports.webglSymbolMapper = webglSymbolMapper;
    exports.webglTypes = types;
    exports.webglUniform = uniform;
    exports.zoom = zoom;

    Object.defineProperty(exports, '__esModule', { value: true });

}));
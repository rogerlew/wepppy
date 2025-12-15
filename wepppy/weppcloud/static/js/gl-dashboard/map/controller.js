/**
 * Deck.gl controller wrapper for gl-dashboard.
 * Owns the Deck instance; accepts callbacks for hover/tooltips/errors/view state.
 * No business logic; no sidebar/DOM manipulation beyond the target element.
 */

export function createMapController({
  deck,
  target,
  controllerOptions,
  initialViewState,
  onHover,
  getTooltip,
  onError,
  onViewStateChange,
  layers = [],
}) {
  const deckgl = new deck.Deck({
    parent: target,
    controller: controllerOptions,
    initialViewState,
    layers,
    onHover,
    getTooltip,
    onError,
    onViewStateChange,
  });

  function applyLayers(nextLayers) {
    deckgl.setProps({ layers: nextLayers });
  }

  function setViewState(viewState) {
    deckgl.setProps({ viewState });
  }

  return {
    deckgl,
    applyLayers,
    setViewState,
  };
}

export function bindFilterControls({ setState } = {}) {
  const rangeInputs = Array.from(document.querySelectorAll('input[name="storm_filter_range"]'));
  const warmupInput = document.querySelector('input[name="storm_warmup"]');

  function updateRangeState(value) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      setState({ filterRangePct: parsed });
    }
  }

  function updateWarmupState(checked) {
    setState({ includeWarmup: Boolean(checked) });
  }

  rangeInputs.forEach((input) => {
    input.addEventListener('change', () => {
      if (input.checked) {
        updateRangeState(input.value);
      }
    });
    if (input.checked) {
      updateRangeState(input.value);
    }
  });

  if (warmupInput) {
    warmupInput.addEventListener('change', () => {
      updateWarmupState(warmupInput.checked);
    });
    updateWarmupState(warmupInput.checked);
  }
}

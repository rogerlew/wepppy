import { afterEach, beforeAll, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { getState, initState, setState, setValue, subscribe } from '../state.js';

let originalState;

beforeAll(() => {
  originalState = JSON.parse(JSON.stringify(getState()));
});

beforeEach(() => {
  initState(originalState);
});

afterEach(() => {
  initState(originalState);
});

describe('storm-event-analyzer state subscriptions', () => {
  it('notifies subscribers on setValue updates', () => {
    const callback = jest.fn();
    const unsubscribe = subscribe(['filterRangePct'], callback);

    setValue('filterRangePct', 5);

    expect(callback).toHaveBeenCalledTimes(1);
    const [, changedKeys] = callback.mock.calls[0];
    expect(changedKeys).toContain('filterRangePct');

    unsubscribe();
  });

  it('skips notifications when silent', () => {
    const callback = jest.fn();
    const unsubscribe = subscribe(['includeWarmup'], callback);

    setState({ includeWarmup: false }, { silent: true });

    expect(callback).not.toHaveBeenCalled();
    unsubscribe();
  });
});

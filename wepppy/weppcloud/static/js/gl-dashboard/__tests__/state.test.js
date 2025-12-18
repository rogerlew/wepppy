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

describe('gl-dashboard state subscriptions', () => {
  it('notifies subscribers with changed keys for setValue', () => {
    const calls = [];
    const unsubscribe = subscribe(['weppStatistic'], (state, changedKeys) => {
      calls.push({ state, changedKeys });
    });

    setValue('weppStatistic', 'median');

    expect(calls).toHaveLength(1);
    expect(calls[0].changedKeys).toContain('weppStatistic');
    expect(calls[0].state.weppStatistic).toBe('median');

    unsubscribe();
  });

  it('respects silent updates and key filters for setState', () => {
    const callback = jest.fn();
    const unsubscribe = subscribe(['weppStatistic'], callback);

    setState({ weppStatistic: 'p90' }, { silent: true });
    expect(callback).not.toHaveBeenCalled();

    setState({ cumulativeMeasure: 'runoff_volume' });
    expect(callback).not.toHaveBeenCalled();

    setState({ weppStatistic: 'sd' });
    expect(callback).toHaveBeenCalledTimes(1);
    const [, changedKeys] = callback.mock.calls[0];
    expect(changedKeys).toContain('weppStatistic');

    unsubscribe();
  });
});

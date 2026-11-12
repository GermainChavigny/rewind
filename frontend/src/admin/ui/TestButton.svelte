<!-- "Test" button: runs one real request with the settings as typed and shows the verdict. -->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import type { CheckResult } from '../api';

  let { run, label = 'Tester' }: { run: () => Promise<CheckResult>; label?: string } = $props();
  let busy = $state(false);
  let result = $state<CheckResult | null>(null);

  async function go() {
    busy = true;
    result = null;
    try {
      result = await run();
    } catch (err) {
      result = { ok: false, message: (err as Error).message || 'Test impossible.' };
    } finally {
      busy = false;
    }
  }
</script>

<div class="test">
  <button onclick={go} disabled={busy}>{#if busy}Test en cours…{:else}<Glyph name="bolt" /> {label}{/if}</button>
  {#if result}
    <p class="verdict" class:good={result.ok}>
      <span class="lamp" class:on={result.ok} class:todo={!result.ok}></span>
      {result.message}
    </p>
  {/if}
</div>

<style>
  .test {
    margin: 4px 0 12px;
  }
  .verdict {
    margin: 8px 0 0;
    padding: 8px 10px;
    border: 2px solid var(--ink);
    background: #ffe2c2;
    font-size: 14px;
  }
  .verdict.good {
    background: #d2f5d8;
  }
</style>

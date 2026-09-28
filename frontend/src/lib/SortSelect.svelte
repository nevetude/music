<script>
  // options: [{ value, label }], первый вариант — значение по умолчанию (решает родитель).
  let { options, value, onchange } = $props();
</script>

<label class="sort-select">
  <select {value} onchange={(e) => onchange(e.currentTarget.value)}>
    {#each options as option (option.value)}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
</label>

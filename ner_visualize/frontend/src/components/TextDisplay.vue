<template>
  <div class="relative border p-4 rounded bg-white shadow">
    <p class="text-lg leading-relaxed">
      <span v-html="highlightedText"></span>
    </p>

    <div class="mt-4 space-y-1">
      <div v-for="(className, type) in legend" :key="type" class="flex items-center gap-2">
        <span :class="`w-4 h-4 inline-block rounded ${className}`"></span>
        <span class="text-sm text-gray-700">{{ type }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import mark from 'mark.js'

// Props
defineProps({
  text: String,
  entities: Object,
  legend: Object
})

// Computed highlight logic
const highlightedText = computed(() => {
  if (!text || !entities) return text

  let result = text
  for (const [entity, type] of Object.entries(entities)) {
    const className = legend[type] || "bg-gray-300"
    const escapedEntity = entity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') // Escape regex
    const regex = new RegExp(`\\b(${escapedEntity})\\b`, 'g')
    result = result.replace(regex, `<span class="${className}" title="${type}">$1</span>`)
  }
  return result
})
</script>


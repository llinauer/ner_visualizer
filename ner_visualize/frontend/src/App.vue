<template>
  <div class="min-h-screen bg-gray-50 text-gray-900 p-4 font-sans">
    <h1 class="text-2xl font-bold mb-4">Entity Annotator</h1>
    <p class="mb-4">{{ text }}</p> <!-- Display the text -->
    
    <div class="mt-6 flex gap-2 flex-wrap">
      <!-- Render buttons dynamically from the backend -->
      <button
        v-for="button in buttons"
        :key="button.label"
        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        @click="handleClick(button)"
      >
        {{ button.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const text = ref('Flask is a micro web framework written in Python. Vue.js is a front-end JavaScript framework.')
const buttons = ref([])  // Button configuration fetched from the backend

// Fetch button configuration from Flask backend
onMounted(async () => {
  const res = await fetch("http://localhost:5000/api/config")
  buttons.value = await res.json()
})

// Handle button click (send text to backend and update entities)
async function handleClick(button) {
  const response = await fetch(`http://localhost:5000${button.url}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text: text.value })
  })
  const entities = await response.json()
  console.log(entities)  // Display the entities in the console
  // Here we will process and highlight the text based on the entities (we'll do this next)
}
</script>

<style>
/* Optional: Tailwind styles for your minimal setup */
</style>

<template>
    <div class="min-h-screen bg-gray-50 text-gray-900 p-4 font-sans">
      <h1 class="text-2xl font-bold mb-4">Configure Buttons</h1>
      
      <!-- List of Buttons -->
      <div class="space-y-2">
        <div v-for="(button, index) in buttons" :key="index" class="flex items-center gap-2">
          <input
            type="text"
            v-model="button.label"
            class="px-4 py-2 border rounded"
            placeholder="Button Label"
          />
          <input
            type="text"
            v-model="button.url"
            class="px-4 py-2 border rounded"
            placeholder="API URL"
          />
          <button
            class="text-red-500"
            @click="removeButton(index)"
          >
            🗑️
          </button>
        </div>
      </div>
      
      <!-- Add Button -->
      <button
        class="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        @click="addButton"
      >
        Add Button
      </button>
  
      <!-- Save Button -->
      <div class="mt-4">
        <button
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          @click="saveConfig"
        >
          Save Configuration
        </button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue'
  
  const buttons = ref([  // Initial dummy button configuration
    { label: 'Highlight Frameworks', url: '/api/highlight/frameworks' },
    { label: 'Highlight Languages', url: '/api/highlight/languages' }
  ])
  
  // Add a new button to the list
  function addButton() {
    buttons.value.push({ label: '', url: '' })
  }
  
  // Remove a button from the list
  function removeButton(index) {
    buttons.value.splice(index, 1)
  }
  
  // Save the current button configuration to the backend
  async function saveConfig() {
    const response = await fetch("http://localhost:5000/api/config", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(buttons.value)
    })
    const result = await response.json()
    if (result.success) {
      alert('Configuration saved!')
    } else {
      alert('Failed to save configuration.')
    }
  }
  </script>
  
  <style>
  /* Optional: Tailwind styles for your config page */
  </style>
  
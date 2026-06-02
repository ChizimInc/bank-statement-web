<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white border-b px-6 py-3 flex items-center gap-6 text-sm">
      <span class="font-bold text-gray-800 mr-4">Bank Statements</span>
      <NuxtLink to="/" class="text-gray-600 hover:text-blue-600" active-class="text-blue-600 font-medium">Import</NuxtLink>
      <NuxtLink to="/rules" class="text-gray-600 hover:text-blue-600" active-class="text-blue-600 font-medium">Rules</NuxtLink>
      <NuxtLink to="/summary" class="text-gray-600 hover:text-blue-600" active-class="text-blue-600 font-medium">Summary</NuxtLink>
    </nav>
    <main class="p-6 max-w-5xl mx-auto">
      <NuxtPage />
    </main>
  </div>
</template>

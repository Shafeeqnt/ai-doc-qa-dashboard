<template>
  <div class="upload-box">
    <h2>📄 Upload PDF</h2>
    <input type="file" @change="onFileChange" />
    <button @click="uploadFile" :disabled="!file">Upload</button>

    <div v-if="response" class="result">
      <p><b>Filename:</b> {{ response.filename }}</p>
      <p><b>Chunks:</b> {{ response.num_chunks }}</p>
      <p><b>Preview:</b> {{ response.preview }}</p>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "FileUpload",
  data() {
    return {
      file: null,
      response: null,
    };
  },
  methods: {
    onFileChange(e) {
      this.file = e.target.files[0];
    },
    async uploadFile() {
      if (!this.file) return;

      const formData = new FormData();
      formData.append("file", this.file);

      try {
        const res = await axios.post("http://127.0.0.1:8000/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        this.response = res.data;

        // Send filename to parent
        this.$emit("uploaded", res.data);
      } catch (err) {
        console.error(err);
        alert("Upload failed");
      }
    },
  },
};
</script>

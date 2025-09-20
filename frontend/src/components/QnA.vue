<template>
  <div class="qna-box">
    <h2>💬 Ask a Question</h2>

    <div class="chat-box">
      <div v-for="(msg, index) in messages" :key="index">
        <div v-if="msg.role === 'user'" class="message-user">
          <span>{{ msg.content }}</span>
        </div>
        <div v-else class="message-ai">
          <span>{{ msg.content }}</span>
        </div>
      </div>
    </div>

    <div class="input-area">
      <input
        v-model="question"
        placeholder="Type your question..."
        @keyup.enter="askQuestion"
      />
      <button @click="askQuestion">Send</button>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "QnA",
  props: ["filename"],
  data() {
    return {
      question: "",
      messages: [],
    };
  },
  methods: {
    async askQuestion() {
      if (!this.question.trim()) return;

      // Show user message
      this.messages.push({ role: "user", content: this.question });
      const q = this.question;
      this.question = "";

      try {
        const formData = new FormData();
        formData.append("filename", this.filename);
        formData.append("question", q);

        const res = await axios.post("http://127.0.0.1:8000/ask", formData);

        this.messages.push({ role: "assistant", content: res.data.answer });
      } catch (err) {
        console.error(err);
        this.messages.push({ role: "assistant", content: "⚠️ Error fetching answer." });
      }
    },
  },
};
</script>

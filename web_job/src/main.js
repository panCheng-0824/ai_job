import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/page-shared.css";
import "./styles/home-layout.css";
import "./styles/side-rail-layout.css";
import "./styles/embed-detail.css";

createApp(App).use(router).mount("#app");

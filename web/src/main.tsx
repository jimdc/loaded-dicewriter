import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import { routerBasename } from "./base";
import "./styles/tokens.css";
import "./styles/base.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing");
}

const basename = routerBasename();

createRoot(root).render(
  <StrictMode>
    {basename ? (
      <BrowserRouter basename={basename}>
        <App />
      </BrowserRouter>
    ) : (
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )}
  </StrictMode>,
);

import { configureStore } from "@reduxjs/toolkit";
import trialsReducer from "./trialsSlice";

export const store = configureStore({
  reducer: { trials: trialsReducer },
});
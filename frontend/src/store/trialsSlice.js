import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8425",
  withCredentials: true,
});

export const fetchTrials = createAsyncThunk(
  "trials/fetch",
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.get("/trials");
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || "Failed to load trials");
    }
  }
);

export const createTrial = createAsyncThunk(
  "trials/create",
  async (trial, { rejectWithValue }) => {
    try {
      const res = await api.post("/trials", trial);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || "Failed to create trial");
    }
  }
);

export const updateTrial = createAsyncThunk(
  "trials/update",
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/trials/${id}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || "Failed to update trial");
    }
  }
);

export const deleteTrial = createAsyncThunk(
  "trials/delete",
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/trials/${id}`);
      return id;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || "Failed to delete trial");
    }
  }
);

const trialsSlice = createSlice({
  name: "trials",
  initialState: { items: [], status: "idle", error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTrials.pending, (state) => { state.status = "loading"; state.error = null; })
      .addCase(fetchTrials.fulfilled, (state, action) => { state.status = "succeeded"; state.items = action.payload; })
      .addCase(fetchTrials.rejected, (state, action) => { state.status = "failed"; state.error = action.payload; })
      .addCase(createTrial.fulfilled, (state, action) => { state.items.push(action.payload); })
      .addCase(createTrial.rejected, (state, action) => { state.error = action.payload; })
      .addCase(updateTrial.fulfilled, (state, action) => {
        const i = state.items.findIndex((t) => t.id === action.payload.id);
        if (i !== -1) state.items[i] = action.payload;
      })
      .addCase(updateTrial.rejected, (state, action) => { state.error = action.payload; })
      .addCase(deleteTrial.fulfilled, (state, action) => {
        state.items = state.items.filter((t) => t.id !== action.payload);
      })
      .addCase(deleteTrial.rejected, (state, action) => { state.error = action.payload; });
  },
});

export default trialsSlice.reducer;
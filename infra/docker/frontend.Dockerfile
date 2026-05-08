FROM node:20-alpine
WORKDIR /app
COPY frontend ./frontend
WORKDIR /app/frontend
RUN npm install
CMD ["npm", "run", "dev"]

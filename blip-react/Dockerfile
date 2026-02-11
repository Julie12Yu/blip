FROM node:18

WORKDIR /blip-react

COPY package*.json ./
RUN npm install

COPY . .

# Build-time env (React bakes REACT_APP_* into the bundle). Provide via --build-arg or .env.
ARG REACT_APP_URL
ARG REACT_APP_KEY
ENV REACT_APP_URL=${REACT_APP_URL}
ENV REACT_APP_KEY=${REACT_APP_KEY}

ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]
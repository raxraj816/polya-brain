# Included router silently drops websocket route

Including a child router under a prefix copies its HTTP routes, but its websocket
route is absent from the parent. Identify the missing dispatch behavior and
propose a correction that preserves the prefix and route name.

module.exports = {
  transformIgnorePatterns: [
    'node_modules/(?!(axios|recharts|d3-.*)/)'
  ],
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest'
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  }
};
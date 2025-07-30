docker run -d \
  --name neo4j-blackcore \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/AHha6LqiznmaVJAMMatj \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  -v $HOME/neo4j/blackcore_data:/data \
  neo4j:5-community
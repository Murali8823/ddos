#!/bin/bash
# 🎯 Scale Bot Army Script

if [ -z "$1" ]; then
    echo "🤖 Bot Army Scaling Script"
    echo ""
    echo "Usage: $0 <number_of_bots>"
    echo ""
    echo "Examples:"
    echo "  $0 5    # Scale to 5 bots"
    echo "  $0 28   # Scale to 28 bots (full army)"
    echo "  $0 50   # Scale to 50 bots (mega army!)"
    echo ""
    echo "Current bot count:"
    docker-compose -f docker-compose.scale.yml ps bot | grep -c "Up"
    exit 1
fi

BOT_COUNT=$1

echo "🚀 Scaling bot army to $BOT_COUNT bots..."

# Scale the bot service
docker-compose -f docker-compose.scale.yml up --scale bot=$BOT_COUNT -d

echo ""
echo "✅ Bot army scaled to $BOT_COUNT bots!"
echo ""
echo "📊 Current status:"
docker-compose -f docker-compose.scale.yml ps

echo ""
echo "🎯 Attack capacity: ~$(($BOT_COUNT * 100)) requests/second"
echo ""
echo "📈 Monitor with:"
echo "  • docker-compose -f docker-compose.scale.yml logs -f bot"
echo "  • docker stats"
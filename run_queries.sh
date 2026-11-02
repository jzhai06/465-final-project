DB="resell.db"

# Run from the folder this script lives in, so relative file names work.
cd "$(dirname "$0")" || exit 1

echo "Recreating database..."
rm -f "$DB"
sqlite3 -bail "$DB" < schema.sql      || { echo "schema.sql failed."; exit 1; }
sqlite3 -bail "$DB" < insert_data.sql || { echo "insert_data.sql failed."; exit 1; }
echo "Database created: $DB"

echo
echo "Running queries..."
# queries.sql and transaction.sql run PRAGMA foreign_keys = ON themselves,
# because SQLite enforces foreign keys per connection.
sqlite3 -header -column "$DB" < queries.sql

echo
echo "Running transaction..."
sqlite3 -header -column -bail "$DB" < transaction.sql
status=$?

if [ "$status" -eq 0 ]; then
    echo
    echo "Transaction completed successfully (rolled back for the demonstration)."
else
    echo
    echo "Transaction failed."
    echo "Uncommitted changes were rolled back."
fi

echo
echo "Done."
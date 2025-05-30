#!/usr/bin/env php
<?php
// Optimized version using numeric IDs for keys

$valid_ext = '/\.(jpg|jpeg|jpe|jp2|jpx|dng|heic|heif|avif|webp|cr2|cr3|nef|arw|orf|rw2|raf|srw|pef|tif|tiff)$/i';
$seen = [];
$count = 0;
$empty_count = 0;
$skipped_ext = 0;
$min_count = 50;
$max_field_length = 50; // Skip fields with names longer than this

// Blacklist of fields to ignore
$field_blacklist = [
    'MEDIAWIKI_EXIF_VERSION' => true,
];

// Map field names to numeric IDs
$field_to_id = [];
$field_count = []; // Track how many times each field appears
$next_id = 0;
$skipped_long_fields = 0;
$skipped_blacklisted = 0;

// Open debug file for keys
$debug = fopen('debug_keys.txt', 'w');

while ($line = fgets(STDIN)) {
    if (strpos($line, 'INSERT INTO `image` VALUES') !== 0) continue;
    
    // Remove the INSERT prefix and split by record boundaries
    $line = substr($line, 27); // Remove "INSERT INTO `image` VALUES ("
    $line = rtrim($line, ");\n\r");
    $records = explode('),(', $line);
    
    foreach ($records as $record) {
        $count++;
        
        // Quick regex to extract just filename and metadata fields
        if (!preg_match("/^'([^']*)',[^,]*,[^,]*,[^,]*,'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'/", $record, $match)) continue;
        
        $filename = $match[1];
        $metadata = $match[2];
        
        // Check extension
        if (!preg_match($valid_ext, $filename)) {
            $skipped_ext++;
            continue;
        }
        
        // Unescape metadata - stripslashes handles \', \", \\, \n, \r, \0
        $metadata = stripslashes($metadata);
        
        $field_ids = [];
        $keys = null;
        
        // Try JSON first
        if ($metadata[0] === '{') {
            $data = @json_decode($metadata, true);
            if ($data && isset($data['data'])) {
                // If exif field exists, use only that
                if (isset($data['data']['exif']) && is_array($data['data']['exif'])) {
                    $keys = array_keys($data['data']['exif']);
                } else {
                    $keys = array_keys($data['data']);
                }
            }
        } 
        // Try PHP serialized
        elseif ($metadata[0] === 'a') {
            $data = @unserialize($metadata);
            if ($data && is_array($data)) {
                // If exif field exists, use only that
                if (isset($data['exif']) && is_array($data['exif'])) {
                    $keys = array_keys($data['exif']);
                } else {
                    $keys = array_keys($data);
                }
            }
        }
        
        // Process keys if we got any
        if ($keys) {
            foreach ($keys as $key) {
                // Skip blacklisted fields
                if (isset($field_blacklist[$key])) {
                    $skipped_blacklisted++;
                    continue;
                }
                
                // Skip fields with overly long names
                if (strlen($key) > $max_field_length) {
                    $skipped_long_fields++;
                    continue;
                }
                
                if (!isset($field_to_id[$key])) {
                    $field_to_id[$key] = $next_id++;
                    $field_count[$key] = 0;
                }
                $field_count[$key]++;
                $field_ids[] = $field_to_id[$key];
            }
        }
        
        if ($field_ids) {
            // Sort for consistent hashing
            sort($field_ids, SORT_NUMERIC);
            
            // Create hash from sorted array
            // PHP doesn't have array_hash, so we use serialize
            $hash = md5(serialize($field_ids));
            
            if (!isset($seen[$hash])) {
                $seen[$hash] = ['count' => 0, 'filename' => $filename, 'field_ids' => $field_ids];
            }
            $seen[$hash]['count']++;
            
            // Output URL when we hit minimum count
            if ($seen[$hash]['count'] == $min_count) {
                echo "https://commons.wikimedia.org/wiki/File:" . $seen[$hash]['filename'] . "\n";
                
                // Write field names to debug file
                $field_names = [];
                foreach ($seen[$hash]['field_ids'] as $id) {
                    $field_names[] = array_search($id, $field_to_id);
                }
                fwrite($debug, implode(', ', $field_names) . "\n");
            }
        } else {
            $empty_count++;
        }
        
        if ($count % 50000 == 0) {
            fwrite(STDERR, "Processed: $count | Unique: " . count($seen) . " | Unique fields: " . count($field_to_id) . "\n");
        }
    }
}

// Count how many met the threshold
$output_count = 0;
foreach ($seen as $data) {
    if ($data['count'] >= $min_count) $output_count++;
}

fwrite(STDERR, "\nTotal records: $count\n");
fwrite(STDERR, "Skipped (wrong extension): $skipped_ext\n");
fwrite(STDERR, "Empty metadata: $empty_count\n");
fwrite(STDERR, "Skipped blacklisted fields: $skipped_blacklisted\n");
fwrite(STDERR, "Skipped long field names: $skipped_long_fields\n");
fwrite(STDERR, "Unique field combinations: " . count($seen) . "\n");
fwrite(STDERR, "Combinations with >= $min_count examples: $output_count\n");
fwrite(STDERR, "Total unique field names seen: " . count($field_to_id) . "\n");

// Sort fields by popularity
arsort($field_count);
fwrite(STDERR, "\nAll EXIF fields by popularity:\n");
$i = 0;
foreach ($field_count as $field => $count) {
    fwrite(STDERR, sprintf("%4d. %-40s %d\n", ++$i, $field, $count));
}

fclose($debug);
?>

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
$make_model_count = []; // Track Make/Model combinations
$software_count = []; // Track Software values
$next_id = 0;
$skipped_long_fields = 0;
$skipped_blacklisted = 0;

// Open debug file for keys
$debug = fopen('debug_keys.txt', 'w');

// Function to print summary
function print_summary() {
    global $count, $skipped_ext, $empty_count, $skipped_blacklisted, $skipped_long_fields;
    global $seen, $min_count, $field_to_id, $software_count;
    
    // Count how many met the threshold
    $output_count = 0;
    foreach ($seen as $data) {
        if ($data['count'] >= $min_count) $output_count++;
    }
    
    fwrite(STDERR, "\n\nSUMMARY:\n");
    fwrite(STDERR, "Total records: $count\n");
    fwrite(STDERR, "Skipped (wrong extension): $skipped_ext\n");
    fwrite(STDERR, "Empty metadata: $empty_count\n");
    fwrite(STDERR, "Skipped blacklisted fields: $skipped_blacklisted\n");
    fwrite(STDERR, "Skipped long field names: $skipped_long_fields\n");
    fwrite(STDERR, "Unique EXIF producers: " . count($seen) . "\n");
    fwrite(STDERR, "Producers with >= $min_count examples: $output_count\n");
    fwrite(STDERR, "Total unique field names seen: " . count($field_to_id) . "\n");
    
    // Sort Software by popularity
    arsort($software_count);
    fwrite(STDERR, "\nTop 100 Software values by popularity:\n");
    $i = 0;
    foreach ($software_count as $software => $software_count_val) {
        fwrite(STDERR, sprintf("%4d. %-50s %d\n", ++$i, $software, $software_count_val));
        if ($i >= 100) break;
    }
}

// Register signal handler for Ctrl+C
pcntl_signal(SIGINT, function($signo) {
    print_summary();
    exit(0);
});

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
        
        $filename = stripslashes($match[1]);
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
        
        $exif_data = null;
        
        // Try JSON first
        if ($metadata[0] === '{') {
            $data = @json_decode($metadata, true);
            if ($data && isset($data['data'])) {
                // If exif field exists, use only that
                if (isset($data['data']['exif']) && is_array($data['data']['exif'])) {
                    $exif_data = $data['data']['exif'];
                    $keys = array_keys($exif_data);
                } else {
                    $exif_data = $data['data'];
                    $keys = array_keys($exif_data);
                }
            }
        } 
        // Try PHP serialized
        elseif ($metadata[0] === 'a') {
            $data = @unserialize($metadata);
            if ($data && is_array($data)) {
                // If exif field exists, use only that
                if (isset($data['exif']) && is_array($data['exif'])) {
                    $exif_data = $data['exif'];
                    $keys = array_keys($exif_data);
                } else {
                    $exif_data = $data;
                    $keys = array_keys($exif_data);
                }
            }
        }
        
        // Track Make/Model combinations and determine EXIF producer key
        $exif_producer_key = '';
        
        if ($exif_data) {
            $make = isset($exif_data['Make']) ? $exif_data['Make'] : '';
            $model = isset($exif_data['Model']) ? $exif_data['Model'] : '';
            
            if ($make || $model) {
                $make_model = trim($make . ' / ' . $model);
                if (!isset($make_model_count[$make_model])) {
                    $make_model_count[$make_model] = 0;
                }
                $make_model_count[$make_model]++;
            }
            
            // Track Software
            if (isset($exif_data['Software']) && $exif_data['Software']) {
                $software = is_array($exif_data['Software']) ? 
                    json_encode($exif_data['Software']) : 
                    (string)$exif_data['Software'];
                if (!isset($software_count[$software])) {
                    $software_count[$software] = 0;
                }
                $software_count[$software]++;
            }
            
            // Determine EXIF producer key with hierarchy
            // 1) Software tag first (plus other software markers)
            $software_tags = [];
            if (isset($exif_data['Software']) && $exif_data['Software']) {
                $software_tags[] = is_array($exif_data['Software']) ? 
                    json_encode($exif_data['Software']) : 
                    (string)$exif_data['Software'];
            }
            // Add other software-related tags
            foreach (['ProcessingSoftware', 'HostComputer', 'Artist'] as $tag) {
                if (isset($exif_data[$tag]) && $exif_data[$tag]) {
                    $software_tags[] = is_array($exif_data[$tag]) ? 
                        json_encode($exif_data[$tag]) : 
                        (string)$exif_data[$tag];
                }
            }
            
            if ($software_tags) {
                $exif_producer_key = 'SOFTWARE:' . implode('|', $software_tags);
            }
            // 2) Make/Model pair if no software
            elseif ($make || $model) {
                $exif_producer_key = 'CAMERA:' . trim($make . '/' . $model);
            }
            // 3) All tag names if neither
            else {
                $exif_producer_key = 'TAGS:' . implode('', $keys);
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
        
        if ($field_ids || $exif_producer_key) {
            // Use EXIF producer key as the primary identifier
            $hash = $exif_producer_key ? md5($exif_producer_key) : md5(serialize($field_ids));
            
            if (!isset($seen[$hash])) {
                $seen[$hash] = ['count' => 0, 'filename' => $filename, 'producer_key' => $exif_producer_key, 'field_ids' => $field_ids];
            }
            $seen[$hash]['count']++;
            
            // Output URL when we hit minimum count
            if ($seen[$hash]['count'] == $min_count) {
                echo "https://commons.wikimedia.org/wiki/File:" . urlencode($seen[$hash]['filename']) . "\n";
                
                // Write producer key or field names to debug file
                if ($seen[$hash]['producer_key']) {
                    fwrite($debug, $seen[$hash]['producer_key'] . "\n");
                } else {
                    $field_names = [];
                    foreach ($seen[$hash]['field_ids'] as $id) {
                        $field_names[] = array_search($id, $field_to_id);
                    }
                    fwrite($debug, 'TAGS:' . implode(', ', $field_names) . "\n");
                }
            }
        } else {
            $empty_count++;
        }
        
        if ($count % 50000 == 0) {
            fwrite(STDERR, "Processed: $count | Unique producers: " . count($seen) . " | Unique field names: " . count($field_to_id) . "\n");
        }
        
        // Handle signals
        pcntl_signal_dispatch();
    }
}

// Print final summary
print_summary();

fclose($debug);
?>

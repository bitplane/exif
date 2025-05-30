#!/usr/bin/env php
<?php
// Use native PHP parsing for both formats

$valid_ext = '/\.(jpg|jpeg|jpe|jp2|jpx|dng|heic|heif|avif|webp|cr2|cr3|nef|arw|orf|rw2|raf|srw|pef)$/i';
$seen = [];
$count = 0;
$empty_count = 0;
$skipped_ext = 0;
$min_count = 20;

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
        
        // Unescape metadata
        $metadata = str_replace('\\"', '"', $metadata);
        $metadata = str_replace('\\\\', '\\', $metadata);
        
        $fields = '';
        
        // Try JSON first
        if ($metadata[0] === '{') {
            $data = @json_decode($metadata, true);
            if ($data && isset($data['data'])) {
                $keys = array_keys($data['data']);
                sort($keys);
                $fields = implode('', $keys);
            }
        } 
        // Try PHP serialized
        elseif ($metadata[0] === 'a') {
            $data = @unserialize($metadata);
            if ($data && is_array($data)) {
                $keys = array_keys($data);
                sort($keys);
                $fields = implode('', $keys);
            }
        }
        
        if ($fields) {
            $hash = md5($fields);
            if (!isset($seen[$hash])) {
                $seen[$hash] = ['count' => 0, 'filename' => $filename, 'fields' => $fields];
            }
            $seen[$hash]['count']++;
            
            // Output URL when we hit minimum count
            if ($seen[$hash]['count'] == $min_count) {
                echo "https://commons.wikimedia.org/wiki/File:" . $seen[$hash]['filename'] . "\n";
                fwrite($debug, $seen[$hash]['fields'] . "\n");
            }
        } else {
            $empty_count++;
        }
        
        if ($count % 50000 == 0) {
            fwrite(STDERR, "Processed: $count | Unique: " . count($seen) . "\n");
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
fwrite(STDERR, "Unique field combinations: " . count($seen) . "\n");
fwrite(STDERR, "Combinations with >= $min_count examples: $output_count\n");

fclose($debug);
?>
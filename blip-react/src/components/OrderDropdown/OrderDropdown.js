import { Input } from '@mantine/core';
import { IconChevronDown, IconFilter } from '@tabler/icons-react';
import  {
    Text,
    Button,
} from '@mantine/core';
import "../FilterDropdown/FilterDropdown.css";

const boldFirstLetter = (text) => {
    return text.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
};

function OrderDropdown({ label, description, options, onChange }) {
  return (
    <div style={{ textAlign: 'left' }}>
        <Input.Wrapper
                id="input-demo"
                label={<Text><IconFilter size={14}/> {label}</Text>}
                px={10}
                description={description}
                >
            <Input
            component="select"
            rightSection={<IconChevronDown size={14} stroke={1.5} className='arrow' />}
            id={`filter-${label}`}
            onChange={(e) => onChange(e.target.value)}
            >
            <option value="">None</option>
                {options.map((option, index) => (
                    <option key={index} value={option}>{boldFirstLetter(option)}</option>
                ))}
            </Input>
        </Input.Wrapper>
    </div>
  );
}

export default OrderDropdown;